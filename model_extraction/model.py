import os
import logging
from copy import deepcopy

from .vfg_edge import VFGEdge
from .vfg_node import VFGNode
from .vfg import VFG
from .log import config_logger


logger = logging.getLogger(__name__)
config_logger(logger)


def _connect_actual_param_nodes(vfg: VFG, subvfg: VFG) -> bool:
    """Pass 3."""
    for i, node in enumerate(subvfg.nodes):
        if node.type == 'ActualParmVFGNode' and node.lower_node_number == 0:
            logger.debug("Pass 3 (node): %d/%d", i + 1, subvfg.node_number)
            if node.function is None or node.basic_block is None:
                logger.warning('ActualParmVFGNode (%d) does not contains necessary information', node.id)
                continue
            ret_nodes = vfg.search_nodes('ActualRetVFGNode', node.function, node.basic_block)
            matched_nodes = [ret_node for ret_node in ret_nodes if node.label in ret_node.ir and not node.has_edge(ret_node.name, 'out')]
            if matched_nodes:
                vfg.add_edge(VFGEdge(node.name, matched_nodes[0].name))
                logger.info("VFG changed when processing ActualParmVFGNode (%d)", node.id)
    return vfg.changed


def _connect_actual_ret_nodes(vfg: VFG, subvfg: VFG):
    """Pass 4."""
    for i, node in enumerate(subvfg.nodes):
        if node.type == 'ActualRetVFGNode' and node.upper_node_number < node.param_number:
            logger.debug("Pass 4 (node): %d/%d", i + 1, subvfg.node_number)
            if node.function is None or node.basic_block is None:
                logger.warning('ActualRetVFGNode (%d) does not contains necessary information', node.id)
                return
            param_nodes = vfg.search_nodes('ActualParmVFGNode', node.function, node.basic_block)
            matched_nodes = [param_node for param_node in param_nodes for param_label in node.params if param_label in param_node.ir and not node.has_edge(node.name, 'in')]
            if matched_nodes:
                for param_node in matched_nodes:
                    vfg.add_edge(VFGEdge(param_node.name, node.name))
                    logger.info("VFG changed when processing ActualRetVFGNode (%d)", node.id)
    return vfg.changed


def _remove_consecutive_gep_nodes(vfg: VFG):
    """Pass 1."""
    _vfg = deepcopy(vfg)
    for i, edge in enumerate(_vfg.edges):
        logger.debug("Pass 1 (edge): %d/%d", i + 1, vfg.edge_number)
        source_node = vfg[edge.source]
        target_node = vfg[edge.target]
        if source_node.type == 'GepVFGNode' and target_node.type == 'GepVFGNode':
            target_node.label = f"{source_node.label}.{'.'.join(target_node.label.split('.')[1:])}"
            # must add_edge before disconnect_node
            for node_name in source_node.upper_node_names:
                vfg.add_edge(VFGEdge(node_name, target_node.name))
            vfg.disconnect_node(source_node.name)
            logger.info("VFG changed when removing \"GepVFGNode (%s)\"", source_node.id)


def _reverse_gep_store_edges(vfg: VFG):
    """Pass 2."""
    _vfg = deepcopy(vfg)
    for i, edge in enumerate(_vfg.edges):
        logger.debug("Pass 2 (edge): %d/%d", i + 1, vfg.edge_number)
        source_node = vfg[edge.source]
        target_node = vfg[edge.target]
        if source_node.type == 'GepVFGNode' and target_node.type == 'StoreVFGNode':
            for e in source_node:
                e.reverse()
            logger.info("VFG changed when reversing Gep-Store edges \"GepVFGNode(%d)\"", source_node.id)


def _merge_gep(vfg: VFG, subvfg: VFG):
    """Pass 5."""
    for i, edge in enumerate(subvfg.edges):
        logger.debug("Pass 5 (edge): %d/%d", i + 1, vfg.edge_number)
        source_node = vfg[edge.source]
        target_node = vfg[edge.target]
        if source_node.type == 'GepVFGNode' and target_node.type == 'LoadVFGNode':
            for lower_node_name in source_node.upper_node_names:
                target_node.label = f'{source_node.label} → {target_node.label.split(" → ")[1]}'
                vfg.add_edge(VFGEdge(lower_node_name, target_node.name))
            vfg.disconnect_node(edge.source)
            logger.info("VFG changed when reversing Gep-Load edges \"GepVFGNode(%d)\"", source_node.id)
        elif target_node.type == 'GepVFGNode' and source_node.type == 'StoreVFGNode':
            for lower_node_name in target_node.lower_node_names:
                source_node.label = f'{source_node.label.split(" → ")[0]} → {target_node.label}'
                vfg.add_edge(VFGEdge(source_node.name, lower_node_name))
            vfg.disconnect_node(edge.target)
            logger.info("VFG changed when reversing Gep-Store edges \"GepVFGNode(%d)\"", source_node.id)


def _remove_unconnected_edges(vfg: VFG) -> None:
    """Pass 6."""
    edge_to_del = [edge for node in vfg for edge in node if not vfg.has_node_name(edge.target) or not vfg.has_node_name(edge.source)]
    for edge in edge_to_del:
        vfg.remove_edge(edge)


def extract_model(vfg: VFG, starting_node_ids: list[int]) -> VFG:
    # Pass 1
    _remove_consecutive_gep_nodes(vfg)

    # Pass 2
    _reverse_gep_store_edges(vfg)

    # Pass 3
    it = 0
    while True:
        it += 1
        logger.info("Pass 3 iteration %d", it)
        subvfg = vfg.get_subgraph(starting_node_ids)
        logger.info("Sub VFG scale: (node: %d, edge: %d)", subvfg.node_number, subvfg.edge_number)
        if not _connect_actual_param_nodes(vfg, subvfg):
            break

    # Pass 4
    it = 0
    while True:
        it += 1
        logger.info("Pass 4 iteration %d", it)
        subvfg = vfg.get_subgraph(starting_node_ids)
        logger.info("Sub VFG scale: (node: %d, edge: %d)", subvfg.node_number, subvfg.edge_number)
        if not _connect_actual_ret_nodes(vfg, subvfg):
            break

    # Pass 5
    # _merge_gep(vfg, subvfg)

    subvfg = vfg.get_subgraph(starting_node_ids)
    logger.info("Sub VFG scale: (node: %d, edge: %d)", subvfg.node_number, subvfg.edge_number)
    _remove_unconnected_edges(subvfg)
    logger.info("Sub VFG scale: (node: %d, edge: %d)", subvfg.node_number, subvfg.edge_number)

    return subvfg
