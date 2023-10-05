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
    'head': re.compile(r'digraph\s+"?([^"]*)"?\s*\{'),
    'rankdir': re.compile(r'rankdir="([^"]*)"'),
    'label': re.compile(r'label="([^"]*)"'),
    'tail': re.compile(r'\}'),
    'node': re.compile(r'(Node0x[0-9a-f]+)\s*\[(.+)\]'),
    'edge': re.compile(r'(Node0x[0-9a-f]+) -> (Node0x[0-9a-f]+)\s*\[(.+)\]'),
    'attr': re.compile(r'(\w+)=((?:[^",]+)|(?:"(?:"|[^"])*"))')
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
        name: str = 'Graph'
        label: str = 'Graph'

        with open(filename, mode='r', encoding="utf-8") as file:
            for i, line in enumerate(file, start=1):
                logger.debug("Reading file \"%s\": %d", filename, i)
                line = line.strip()

                if not line:
                    continue

                for pattern_name, pattern in DOT_PATTERNS.items():
                    match = pattern.match(line)
                    if match:
                        break
                else:
                    raise ValueError(f"Unrecognized line: {line}")

                if pattern_name == 'node':
                    attr_match: list[tuple[str,str]] = DOT_PATTERNS['attr'].findall(match[2])
                    nodes.add(Node(name=match[1], **{key: value.strip('"') for key, value in attr_match}))
                elif pattern_name == 'edge':
                    attr_match: list[tuple[str,str]] = DOT_PATTERNS['attr'].findall(match[3])
                    edges.add(Edge(match[1], match[2], **{key: value.strip('"') for key, value in attr_match}))
                elif pattern_name == 'head':
                    name = match[1]
                elif pattern_name == 'rankdir':
                    pass
                elif pattern_name == 'label':
                    label = match[1]
                elif pattern_name == 'tail':
                    continue
                else:
                    raise ValueError(f"Unknown pattern name: {pattern_name}")

        return cls(nodes, edges, name=name, label=label)
