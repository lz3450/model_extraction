from __future__ import annotations
from typing import Iterable
import re
from .log import get_logger

logger = get_logger(__name__)


class Node:
    def __init__(self, name: str, label: str, shape: str = 'record', color: str = 'black', penwidth: str = '1') -> None:
        self.name = name
        self.label = label
        self.shape = shape
        self.color = color
        self.penwidth = int(penwidth)

    def __str__(self):
        return f'{self.name} [shape={self.shape},color={self.color},penwidth={self.penwidth},label="{{{self.label}}}"];'

    def __eq__(self, other) -> bool:
        if isinstance(other, Node):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)


class Edge:
    def __init__(self, source: str, target: str, style: str = 'solid', color: str = 'black') -> None:
        self.source = source
        self.target = target
        self.style = style
        self.color = color

    def __str__(self):
        return f'{self.source} -> {self.target} [style={self.style},color={self.color}];'

    def __eq__(self, other) -> bool:
        if isinstance(other, Edge):
            return self.source == other.source and self.target == other.target
        return False

    def __hash__(self) -> int:
        return hash((self.source, self.target))


DOT_PATTERNS: dict[str, re.Pattern] = {
    'name': re.compile(r'digraph\s+"?([^"]*)"?\s*\{'),
    'label': re.compile(r'label="([^"]*)"'),
    'node': re.compile(r'(Node0x[0-9a-f]+)\s*\[(.+)\];'),
    'edge': re.compile(r'(Node0x[0-9a-f]+) -> (Node0x[0-9a-f]+)\s*\[(.+)\];'),
    'attr': re.compile(r'(\w+)=((?:[^",]+)|(?:\"(?:\\\"|[^\"])*\"))')
}


class Graph:
    def __init__(self, nodes: Iterable[Node], edges: Iterable[Edge], name: str = 'Graph', label: str = 'Graph') -> None:
        self.nodes = set(nodes)
        self.edges = set(edges)
        self.name = name
        self.label = label

    def __repr__(self) -> str:
        return f'Graph({len(self.nodes)},{len(self.edges)})'

    @property
    def size(self) -> tuple[int, int]:
        return len(self.nodes), len(self.edges)

    def write(self, filename: str):
        with open(filename, mode='w', encoding='utf-8') as file:
            file.write(f'digraph "{self.name}"')
            file.write('{\n')
            file.write('\trankdir="LR";\n')
            file.write(f'\tlabel="{self.label}";\n\n')
            for node in sorted(self.nodes, key=lambda node: int(node.name)):
                file.write(f'\t{node}\n')
            for edge in sorted(self.edges, key=lambda edge: (int(edge.source), int(edge.target))):
                file.write(f'\t{edge}\n')
            file.write("}\n")

    @classmethod
    def from_file(cls, filename: str):
        nodes: set[Node] = set()
        edges: set[Edge] = set()
        name: str | None = None
        label: str | None = None

        with open(filename, mode='r', encoding="utf-8") as file:
            for i, line in enumerate(file):
                logger.debug("Reading file \"%s\": %d", filename, i + 1)
                line = line.strip()

                # Check if the line contains a node description
                node_match = DOT_PATTERNS['node'].match(line)
                if node_match:
                    attr_match: list[str] = DOT_PATTERNS['attr'].findall(node_match[2])
                    node_attrs = {key: value.strip('"') for key, value in attr_match}
                    nodes.add(Node(name=node_match[1], **node_attrs))
                    continue

                # Check if the line contains an edge description
                edge_match = DOT_PATTERNS['edge'].match(line)
                if edge_match:
                    attr_match: list[str] = DOT_PATTERNS['attr'].findall(edge_match[3])
                    edge_attrs = {key: value.strip('"') for key, value in attr_match}
                    edges.add(Edge(edge_match[1], edge_match[2], **edge_attrs))
                    continue

                name_match = DOT_PATTERNS['name'].match(line)
                if name_match:
                    name = name_match[1]
                    continue

                label_match = DOT_PATTERNS['label'].match(line)
                if label_match:
                    label = label_match[1]
                    continue

                graph_attr_match = DOT_PATTERNS['attr'].match(line)
                if graph_attr_match:
                    continue

                if not line or line == '}':
                    continue

                raise ValueError(f"Unrecognized line: {line}")

        return cls(nodes,
                   edges,
                   name=name if name else 'Graph',
                   label=label if label else 'Graph')
