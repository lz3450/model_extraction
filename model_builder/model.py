from __future__ import annotations
from typing import Iterable, Iterator
from itertools import pairwise
from .graph import Node, Edge, Graph
from .vfg import VFGNode, VFG
from .log import get_logger

logger = get_logger(__name__)


class ModelNode:
    def __init__(self, id: int, label: str = '(none)') -> None:
        self.id = id
        self.label = label
        self._lower_nodes: set[ModelNode] = set()

    @property
    def lower_nodes(self) -> Iterator[ModelNode]:
        yield from self._lower_nodes

    def add_lower_nodes(self, node: ModelNode):
        if node != self:
            self._lower_nodes.add(node)

    def __eq__(self, other) -> bool:
        if isinstance(other, ModelNode):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)


class Model:
    def __init__(self, vfg: VFG, start_vfg_node_ids: Iterable[int]):
        self.vfg = vfg
        self.nodes = {}

        paths = self._get_vfg_path(self.vfg.get_node_from_id(id) for id in start_vfg_node_ids)
        for i, path in enumerate(paths):
            logger.debug('%d:', i + 1)
            logger.debug(', '.join(f'{node.type}({node.id})' for node in path))
            logger.debug(''.join(str(node.t) for node in path))
            model_nodes: list[ModelNode] = []
            for vfg_node in path:
                model_node = self.get_node(vfg_node.id)
                model_node.label = vfg_node.label
                model_nodes.append(model_node)
            for upper_node, lower_node in pairwise(model_nodes):
                upper_node.add_lower_nodes(lower_node)

    def __iter__(self) -> Iterator[ModelNode]:
        yield from sorted(self.nodes.values(), key=lambda node: node.id)

    def __getitem__(self, id: int):
        return self.nodes[id]

    def _get_source_sink_vfg_nodes(self, start_vfg_nodes: Iterable[VFGNode]) -> set[VFGNode]:
        source_sink_vfg_nodes: set[VFGNode] = set()

        def _connect_actual_param_ret(actual_parm: VFGNode):
            logger.debug("Actual_Parm_Ret(%d)", actual_parm.id)
            if not actual_parm.function or not actual_parm.basic_block:
                logger.warning('%s(%d) does not contains necessary information', actual_parm.type, actual_parm.id)
            ret_nodes = self.vfg.search_nodes('ActualRet', actual_parm.function, actual_parm.basic_block)
            actual_ret_nodes = [ret_node for ret_node in ret_nodes if actual_parm.parm in ret_node.args]
            for actual_ret in actual_ret_nodes:
                logger.info("Actual_Parm_Ret(%d, %d)", actual_parm.id, actual_ret.id)
                actual_parm.add_lower_nodes(actual_ret)
                actual_ret.add_upper_nodes(actual_parm)

        def _find_source_sink_vfg_nodes(current_vfg_node: VFGNode):
            match current_vfg_node.type:
                case 'ActualParm':
                    _connect_actual_param_ret(current_vfg_node)
                case 'Store' | 'Addr':
                    source_sink_vfg_nodes.add(current_vfg_node)
            if current_vfg_node.lower_node_number == 0:
                return
            for lower_vfg_node in current_vfg_node.lower_nodes:
                _find_source_sink_vfg_nodes(lower_vfg_node)

        for start_vfg_node in start_vfg_nodes:
            _find_source_sink_vfg_nodes(start_vfg_node)

        return source_sink_vfg_nodes

    def _get_vfg_path(self, start_vfg_nodes: Iterable[VFGNode]) -> list[list[VFGNode]]:
        paths: list[list[VFGNode]] = []

        def _find_paths(direction: str, current_path: list[VFGNode]):
            if direction == 'f':
                current_node = current_path[-1]
                if current_node.lower_node_number == 0:
                    paths.append(current_path)
                    logger.info('%d:', len(paths))
                    logger.info(', '.join(f'{node.type}({node.id})' for node in current_path))
                    logger.info(''.join(str(node.t) for node in current_path))
                    return
                for lower_node in current_node.lower_nodes:
                    if lower_node not in current_path:
                        _find_paths(direction, current_path + [lower_node])
                    else:
                        logger.warning("Loop detected!")
            elif direction == 'b':
                current_node = current_path[0]
                if current_node.upper_node_number == 0:
                    paths.append(current_path)
                    logger.info('%d:', len(paths))
                    logger.info(', '.join(f'{node.type}({node.id})' for node in current_path))
                    logger.info(''.join(str(node.t) for node in current_path))
                    return
                for upper_node in current_node.upper_nodes:
                    if upper_node not in current_path:
                        _find_paths(direction, [upper_node] + current_path)
                    else:
                        logger.warning("Loop detected!")
            else:
                raise ValueError('Unknown direction')

        source_sink_vfg_nodes = self._get_source_sink_vfg_nodes(start_vfg_nodes)

        for source_sink_vfg_node in source_sink_vfg_nodes:
            if source_sink_vfg_node.lower_node_number > 0:
                _find_paths('f', current_path=[source_sink_vfg_node])
            if source_sink_vfg_node.upper_node_number > 0:
                _find_paths('b', current_path=[source_sink_vfg_node])

        return paths

    def get_node(self, id: int) -> ModelNode:
        return self.nodes.setdefault(id, ModelNode(id))

    def write(self, filename: str, name: str, label: str):
        nodes: set[Node] = {Node(str(node.id), node.label) for node in self}
        edges: set[Edge] = {Edge(str(node.id), str(lower_node.id)) for node in self for lower_node in node.lower_nodes}
        graph = Graph(nodes, edges, name, label)
        logger.info("Model size: %s", graph.size)
        graph.write(filename)
