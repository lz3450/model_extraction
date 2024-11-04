from __future__ import annotations
from typing import Iterable, Iterator
from itertools import pairwise
import re
from collections import Counter
from .graph import Node, Edge, Graph
from .vfg import VFGNode, VFG
from .log import get_logger

logger = get_logger(__name__)


MODEL_NODE_COLOR: dict[str, str] = {
    'Gep': 'purple'
}

MODEL_NODE_PEN_WIDTH: dict[str, str] = {
    'Gep': '2'
}

PATTERNS: dict[str, str] = {
    'AGL': r'(?<=a)(?P<AGL>g+l)',
    'LGL': r'(?P<LGL>lg+l)',
    'GS': r'(?P<GS>g+s)',
    'AS': r'(?P<AS>as)',
    'CS': r'(?P<CS>cs)',
    'P': r'(?P<P>.*p<)',
    '.': r'.'
}


class ModelNode:
    def __init__(self, id: int, pattern: str, vfg_path_slice: list[VFGNode]) -> None:
        self.id = id
        self.type = pattern
        self.info = self._get_info(vfg_path_slice)
        self._lower_nodes: set[ModelNode] = set()

    def _get_info(self, vfg_path_slice: list[VFGNode]) -> str:
        match self.type:
            case 'AGL':
                info = '.'.join(vfg_node.ptr for vfg_node in vfg_path_slice) + f' → {vfg_path_slice[-1].var}'
            case 'LGL':
                info = vfg_path_slice[0].ptr + ' → '
                info += '.'.join(node.elementptr for node in vfg_path_slice[1:-1])
                info += ' → ' + vfg_path_slice[-1].var
            case 'GS':
                store_vfg_node = vfg_path_slice[-1]
                try:
                    var = self.store_var
                except AttributeError:
                    var = store_vfg_node.var
                info = var + ' → ' + '.'.join(vfg_node.ptr for vfg_node in vfg_path_slice)
            case 'CS':
                copy_vfg_node = vfg_path_slice[0]
                store_vfg_node = vfg_path_slice[1]
                self._store_var = copy_vfg_node.from_var
                info = self.store_var + ' → ' + store_vfg_node.ptr
            case 'AS':
                info = vfg_path_slice[0].compiled_info
            case 'Single':
                self.type = vfg_path_slice[0].type
                info = vfg_path_slice[0].compiled_info
            case _:
                raise ValueError(f'Unknown pattern: {self.type}')
        return info

    def __eq__(self, other) -> bool:
        if isinstance(other, ModelNode):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return self.type + f'({self.id})'

    @property
    def lower_nodes(self) -> Iterator[ModelNode]:
        yield from self._lower_nodes

    @property
    def label(self) -> str:
        return f'{self.type}({self.id})\\n{self.info}'

    @property
    def store_var(self) -> str:
        return self._store_var

    def add_lower_nodes(self, node: ModelNode):
        if node != self:
            self._lower_nodes.add(node)


class Model:
    # pattern = re.compile(r'(?<=a|l)(?P<GL>g+l)|(?P<GS>g+s)|(?P<AS>as)|(?P<CS>cs)|(?P<P>.*p<)|.')
    pattern = re.compile(r'|'.join(PATTERNS.values()))

    def __init__(self, vfg: VFG, start_vfg_node_ids: Iterable[int], opt: bool = True):
        self.vfg = vfg
        self.nodes = {}
        process = self._opt if opt else self._no_opt

        paths = self._get_vfg_path(self.vfg.get_node_from_id(id) for id in start_vfg_node_ids)
        for i, path in enumerate(paths):
            logger.debug('%d:', i + 1)
            logger.debug(', '.join(f'{node.type}({node.id})' for node in path))
            logger.debug(''.join(node.t for node in path))
            process(path)

        type_counts = Counter(node.type for node in self)
        logger.info('Model counts:')
        for type, count in type_counts.items():
            logger.debug('\t%s: %d', type, count)

    def __iter__(self) -> Iterator[ModelNode]:
        yield from sorted(self.nodes.values(), key=lambda node: node.id)

    def __getitem__(self, id: int):
        return self.nodes[id]

    def _get_source_sink_vfg_nodes(self, start_vfg_nodes: Iterable[VFGNode]) -> set[VFGNode]:
        source_sink_vfg_nodes: set[VFGNode] = set()

        def _connect_actual_parm_ret(actual_parm: VFGNode):
            logger.debug("Actual_Parm_Ret(%d)", actual_parm.id)
            if not actual_parm.function or not actual_parm.basic_block:
                logger.warning('%s(%d) does not contains necessary information', actual_parm.type, actual_parm.id)
            ret_nodes = self.vfg.search_nodes('ActualRet', actual_parm.function, actual_parm.basic_block)
            actual_ret_nodes = [ret_node for ret_node in ret_nodes if actual_parm.parm in ret_node.args]
            for actual_ret in actual_ret_nodes:
                logger.debug("Actual_Parm_Ret(%d, %d)", actual_parm.id, actual_ret.id)
                actual_parm.add_lower_nodes(actual_ret)
                actual_ret.add_upper_nodes(actual_parm)

        def _connect_actual_ret_parm(actual_ret: VFGNode):
            logger.debug("Actual_Ret_Parm(%d)", actual_ret.id)
            if not actual_ret.function or not actual_ret.basic_block:
                logger.warning('%s(%d) does not contains necessary information', actual_ret.type, actual_ret.id)
            parm_nodes = self.vfg.search_nodes('ActualParm', actual_ret.function, actual_ret.basic_block)
            actual_parm_nodes = [parm_node for parm_node in parm_nodes if parm_node.parm in actual_ret.args]
            for actual_parm in actual_parm_nodes:
                logger.debug("Actual_Ret_Parm(%d, %d)", actual_ret.id, actual_parm.id)
                actual_parm.add_lower_nodes(actual_ret)
                actual_ret.add_upper_nodes(actual_parm)

        def _find_source_sink_vfg_nodes(current_vfg_node: VFGNode):
            match current_vfg_node.type:
                case 'ActualParm':
                    _connect_actual_parm_ret(current_vfg_node)
                case 'ActualRet':
                    _connect_actual_ret_parm(current_vfg_node)
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
                    logger.debug('%d:', len(paths))
                    logger.debug(', '.join(f'{node.type}({node.id})' for node in current_path))
                    logger.debug(''.join(node.t for node in current_path))
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
                    logger.debug('%d:', len(paths))
                    logger.debug(', '.join(f'{node.type}({node.id})' for node in current_path))
                    logger.debug(''.join(node.t for node in current_path))
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

    def _no_opt(self, path: list[VFGNode]):
        model_nodes: list[ModelNode] = []
        for vfg_node in path:
            model_node = self.get_node('Single', [vfg_node])
            model_nodes.append(model_node)
        for upper_node, lower_node in pairwise(model_nodes):
            upper_node.add_lower_nodes(lower_node)

    def _opt(self, vfg_path: list[VFGNode]):

        def _get_vfg_path_slice(pattern: str):
            logger.debug('Pattern: %s[%s]', pattern, ', '.join(f'{vfg_node.type}({vfg_node.id})' for vfg_node in vfg_path_slice))
            return vfg_path[m.start(pattern):m.end(pattern)]

        logger.debug('Opt VFG path: %s', ', '.join(f'{vfg_node.type}({vfg_node.id})' for vfg_node in vfg_path))
        logger.debug('Opt VFG path: %s', ''.join(vfg_node.t for vfg_node in vfg_path))
        model_path: list[ModelNode] = []
        need_reverse = False
        for m in self.pattern.finditer(''.join(vfg_node.t for vfg_node in vfg_path)):
            if m['AGL']:
                pattern = 'AGL'
                vfg_path_slice = _get_vfg_path_slice(pattern)
                model_path.append(self.get_node(pattern, vfg_path_slice))
            elif m['LGL']:
                pattern = 'LGL'
                vfg_path_slice = _get_vfg_path_slice(pattern)
                model_path.append(self.get_node(pattern, vfg_path_slice))
            elif m['GS']:
                pattern = 'GS'
                need_reverse = True
                vfg_path_slice = _get_vfg_path_slice(pattern)
                model_node = self.get_node(pattern, vfg_path_slice)
                model_path.append(model_node)
            elif m['AS']:
                pattern = 'AS'
                need_reverse = True
                vfg_path_slice = vfg_path[m.start(pattern):m.end(pattern)]
                logger.debug('Pattern: %s[%s]', pattern, ', '.join(f'{vfg_node.type}({vfg_node.id})' for vfg_node in vfg_path_slice))
                model_path.append(self.get_node(pattern, vfg_path_slice[:1]))
                model_path.append(self.get_node(pattern, vfg_path_slice[1:]))
            elif m['CS']:
                pattern = 'CS'
                vfg_path_slice = vfg_path[m.start(pattern):m.end(pattern)]
                logger.debug('Pattern: %s[%s]', pattern, ', '.join(f'{vfg_node.type}({vfg_node.id})' for vfg_node in vfg_path_slice))
                model_node = self.get_node(pattern, vfg_path_slice)
                model_path.append(model_node)
            elif m['P']:
                pattern = 'P'
                vfg_path_slice = vfg_path[m.start(pattern):m.end(pattern)]
                logger.debug('Pattern: %s[%s]', pattern, ', '.join(f'{vfg_node.type}({vfg_node.id})' for vfg_node in vfg_path_slice))
            else:
                pattern = 'Single'
                vfg_path_slice = vfg_path[m.start():m.end()]
                logger.debug('Pattern: %s[%s]', pattern, ', '.join(f'{vfg_node.type}({vfg_node.id})' for vfg_node in vfg_path_slice))
                model_path.append(self.get_node(pattern, vfg_path_slice))
        if need_reverse:
            model_path.reverse()
        for upper_node, lower_node in pairwise(model_path):
            upper_node.add_lower_nodes(lower_node)

    def get_node(self, pattern: str, vfg_path_slice: list[VFGNode]) -> ModelNode:
        match pattern:
            case 'AGL' | 'LGL' | 'GS' | 'CS':
                # Use ID of the last VFG node
                id = vfg_path_slice[-1].id
            case 'AS' | 'Single':
                # Use ID of the first VFG node
                id = vfg_path_slice[0].id
            case _:
                raise ValueError(f'Unknown pattern: {pattern}')
        model_node: ModelNode = self.nodes.setdefault(id, ModelNode(id, pattern, vfg_path_slice))
        return model_node

    def write(self, filename: str, name: str, label: str):
        nodes: set[Node] = {Node(str(node.id),
                                 node.label,
                                 color=MODEL_NODE_COLOR.get(node.type, 'black'),
                                 penwidth=MODEL_NODE_PEN_WIDTH.get(node.type, '1')
                                 ) for node in self}
        edges: set[Edge] = {Edge(str(node.id),
                                 str(lower_node.id)) for node in self for lower_node in node.lower_nodes}
        graph = Graph(nodes, edges, name, label)
        logger.info("Model size: %s", graph.size)
        graph.write(filename)
