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
        self._lower_nodes.add(node)

    def __eq__(self, other) -> bool:
        if isinstance(other, ModelNode):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)


class Model:
    def __init__(self, nodes: Iterable[ModelNode]) -> None:
        self.nodes = {node.id: node for node in nodes}

    def __iter__(self) -> Iterator[ModelNode]:
        yield from sorted(self.nodes.values(), key=lambda node: node.id)

    def __getitem__(self, id: int):
        return self.nodes[id]

    def get_node(self, id: int, label: str) -> ModelNode:
        return self.nodes.get(id, ModelNode(id, label))

    def update(self, nodes: Iterable[ModelNode]):
        self.nodes.update({node.id: node for node in nodes})

    def write(self, filename: str, name: str, label: str):
        nodes: set[Node] = {Node(str(node.id), node.label) for node in self}
        edges: set[Edge] = {Edge(str(node.id), str(lower_node.id)) for node in self for lower_node in node.lower_nodes}
        Graph(nodes, edges, name, label).write(filename)

    @classmethod
    def build_model(cls, vfg: VFG, start_node_ids: Iterable[int]) -> Model:
        start_nodes = set(vfg.get_node_from_id(id) for id in start_node_ids)
        model = cls(ModelNode(vfg_node.id, vfg_node.label) for vfg_node in start_nodes)

        paths = vfg.get_paths(start_node_ids)
        for i, path in enumerate(paths):
            logger.info('%d:', i+1)
            logger.info(', '.join(str(node.id) for node in path))
            logger.info(', '.join(str(node.type) for node in path))
            logger.info(''.join(str(node.t) for node in path))
            nodes: list[ModelNode] = []
            for node in path:
                nodes.append(model.get_node(node.id, node.label))
            for n1, n2 in pairwise(nodes):
                n1.add_lower_nodes(n2)
            model.update(nodes)

        return model
