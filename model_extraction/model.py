import logging
from copy import deepcopy
from typing import Iterable

from .vfg_edge import VFGEdge
from .vfg import VFG
from .log import config_logger


logger = logging.getLogger(__name__)
config_logger(logger)


def _connect_actual_param_nodes(vfg: VFG, starting_node_ids: Iterable[int]):
    """Parm -> Ret"""
    it = 0
    vfg_changed = True
    while vfg_changed:
        it += 1
        vfg_changed = False
        logger.info("Parm_Ret: %d", it)
        subvfg = vfg.get_subgraph(starting_node_ids)
        for i, node in enumerate(subvfg.nodes):
            logger.debug("Parm_Ret: %d/%d", i + 1, subvfg.node_number)
            if node.type == 'ActualParmVFGNode':
                logger.info("Parm_Ret(%d)", node.id)
                if node.function is None or node.basic_block is None:
                    logger.warning('ActualParmVFGNode (%d) does not contains necessary information', node.id)
                    continue
                ret_nodes = vfg.search_nodes('ActualRetVFGNode', node.function, node.basic_block)
                matched_nodes = [ret_node for ret_node in ret_nodes if node.label in ret_node.ir and not node.has_edge(ret_node.name, 'out')]
                for matched_node in matched_nodes:
                    vfg.add_edge(VFGEdge(node.name, matched_node.name))
                    vfg_changed = True
                    logger.info("VFG changed (%d, %d)", node.id, matched_node.id)


def _connect_actual_ret_nodes(vfg: VFG, starting_node_ids: Iterable[int]):
    """Ret -> Parm"""
    it = 0
    vfg_changed = True
    while vfg_changed:
        it += 1
        vfg_changed = False
        logger.info("Ret_Parm: %d", it)
        subvfg = vfg.get_subgraph(starting_node_ids)
        for i, node in enumerate(subvfg.nodes):
            logger.debug("Ret_Parm: %d/%d", i + 1, subvfg.node_number)
            if node.type == 'ActualRetVFGNode':
                logger.info("Ret_Parm(%d)", node.id)
                if node.function is None or node.basic_block is None:
                    logger.warning('ActualRetVFGNode (%d) does not contains necessary information', node.id)
                    return
                param_nodes = vfg.search_nodes('ActualParmVFGNode', node.function, node.basic_block)
                matched_nodes = [param_node for param_node in param_nodes for param_label in node.params if param_label in param_node.ir and not node.has_edge(node.name, 'in')]
                if matched_nodes:
                    for param_node in matched_nodes:
                        vfg.add_edge(VFGEdge(param_node.name, node.name))
                        vfg_changed = True
                        logger.info("VFG changed (%d, %d)", param_node.id, node.id)


def _get_leaf_store_nodes(subvfg: VFG) -> set[int]:
    leaf_store_nodes = set()
    leaf_nodes = subvfg.get_leaf_nodes()

    for node in leaf_nodes:
        if node.type == 'StoreVFGNode':
            leaf_store_nodes.add(node.id)
    logger.info("Found leaf StoreVFGNode: %s", leaf_store_nodes)
    return leaf_store_nodes


def _merge_gep_gep(vfg: VFG, starting_node_ids: Iterable[int]):
    """Remove consecutive GepVFGNode."""
    it = 0
    vfg_changed = True
    while vfg_changed:
        it += 1
        vfg_changed = False
        logger.info("Merge_GepGep: %d", it)
        subvfg = vfg.get_subgraph(starting_node_ids)
        for i, edge in enumerate(subvfg.edges):
            logger.debug("Merge_GepGep: %d/%d", i + 1, subvfg.edge_number)
            source_node, target_node = vfg[edge.source], vfg[edge.target]
            if source_node.type == 'GepVFGNode' and target_node.type == 'GepVFGNode':
                logger.info("Merge_GepGep(%d, %d)", source_node.id, target_node.id)
                target_node.label = f"{source_node.label}.{'.'.join(target_node.label.split('.')[1:])}"
                # must add_edge before disconnect_node
                for upper_node_name in source_node.upper_node_names:
                    vfg.add_edge(VFGEdge(upper_node_name, target_node.name))
                vfg.disconnect_node(source_node.name)
                vfg_changed = True
                logger.info("%s disconnected", source_node.id)
                break


def _merge_gep_load_store(vfg: VFG, starting_node_ids: Iterable[int]):
    """Merge GepVFGNode with LoadVFGNode and StoreVFGNode."""
    subvfg = vfg.get_subgraph(starting_node_ids)
    source_nodes: set[str] = set()
    for i, edge in enumerate(subvfg.edges):
        logger.debug("Merge_Gep: %d/%d", i + 1, subvfg.edge_number)
        source_node, target_node = vfg[edge.source], vfg[edge.target]
        if source_node.type == 'GepVFGNode' and target_node.type in ('LoadVFGNode', 'StoreVFGNode'):
            logger.info("Merge_Gep(%d, %d)", source_node.id, target_node.id)
            for upper_node_name in source_node.upper_node_names:
                vfg.add_edge(VFGEdge(upper_node_name, target_node.name))
            source_nodes.add(source_node.name)
            if target_node.type == 'LoadVFGNode':
                target_node.label = f'{source_node.label} → {target_node.label.split(" → ")[1]}'
            elif target_node.type == 'StoreVFGNode':
                target_node.label = f'{target_node.label.split(" → ")[0]} → {source_node.label}'
            else:
                raise ValueError(edge)
            logger.info("VFG changed (%d)", source_node.id)
    for node_name in source_nodes:
        vfg.disconnect_node(node_name)


def _merge_copy(vfg: VFG, starting_node_ids: Iterable[int]):
    """Merge CopyVFGNode with its lower nodes."""
    subvfg = vfg.get_subgraph(starting_node_ids)
    for i, edge in enumerate(subvfg.edges):
        logger.debug("Merge_Copy: %d/%d", i + 1, subvfg.edge_number)
        source_node = vfg[edge.source]
        target_node = vfg[edge.target]
        if source_node.type == 'CopyVFGNode' and target_node.type in ('StoreVFGNode'):
            logger.info("Merge_Copy(%d, %d)", source_node.id, target_node.id)
            for upper_node_name in source_node.upper_node_names:
                vfg.add_edge(VFGEdge(upper_node_name, target_node.name))
            vfg.disconnect_node(edge.source)
            target_node.label = f'{source_node.label} → {target_node.label.split(" → ")[1]}'
            logger.info("VFG changed (%d)", source_node.id)


def _merge_load_load(vfg: VFG, starting_node_ids: Iterable[int]):
    """"""
    subvfg = vfg.get_subgraph(starting_node_ids)
    # All upper LoadVFGNodes should be disconnected at the end of this pass
    source_nodes: set[str] = set()
    for i, edge in enumerate(subvfg.edges):
        logger.debug("Merge_Load_Load: %d/%d", i + 1, subvfg.edge_number)
        source_node = vfg[edge.source]
        target_node = vfg[edge.target]
        if source_node.type == 'LoadVFGNode' and target_node.type == 'LoadVFGNode':
            logger.info("Merge_Load_Load(%d, %d)", source_node.id, target_node.id)
            target_node.label = f'{source_node.label}\\n{target_node.label}'
            for upper_node_name in source_node.upper_node_names:
                vfg.add_edge(VFGEdge(upper_node_name, target_node.name))
                source_nodes.add(edge.source)
            logger.info("VFG changed (%d)", source_node.id)
    for node_name in source_nodes:
        vfg.disconnect_node(node_name)


def _reverse_addr_store_edges(subvfg: VFG):
    """"""
    for i, edge in enumerate(subvfg.edges):
        logger.debug("Rev_Addr_Store: %d/%d", i + 1, subvfg.edge_number)
        source_node = subvfg[edge.source]
        target_node = subvfg[edge.target]
        if source_node.type == 'AddrVFGNode' and target_node.type == 'StoreVFGNode':
            logger.info("Rev_Addr_Store(%d, %d)", source_node.id, target_node.id)
            edge.reverse()
            logger.info("Sub VFG changed (%d)", source_node.id)


def extract_model(vfg: VFG, starting_node_ids: Iterable[int]) -> VFG:
    ids = set(starting_node_ids)
    while True:
        _connect_actual_param_nodes(vfg, ids)
        _connect_actual_ret_nodes(vfg, ids)
        subvfg = vfg.get_subgraph(ids)
        leaf_store_nodes = _get_leaf_store_nodes(subvfg)
        old_ids_len = len(ids)
        ids.update(leaf_store_nodes)
        if len(ids) == old_ids_len:
            break

    _merge_gep_gep(vfg, ids)
    _merge_gep_load_store(vfg, ids)
    _merge_copy(vfg, ids)
    _merge_load_load(vfg, ids)
    subvfg = vfg.get_subgraph(ids)
    subvfg.remove_unconnected_edges()
    _reverse_addr_store_edges(subvfg)

    logger.info("Model scale: %d nodes, %d edges", subvfg.node_number, subvfg.edge_number)

    return subvfg
