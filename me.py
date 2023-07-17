from __future__ import annotations
from typing import Set, Dict, List, Tuple, Union, Optional, Iterator
import re


class Edge:
    def __init__(self, source: str, target: str):
        self._source = source
        self._target = target

    @property
    def source(self) -> str:
        return self._source

    @property
    def target(self) -> str:
        return self._target


class Node:
    def __init__(self, name: str, label: str):
        self._name = name
        self._label = label
        self._edges: List[Edge] = []
        self._type, self._id = self._parse_label()

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def id(self) -> int:
        return self._id

    @property
    def label(self) -> str:
        return self._label

    def _parse_label(self):
        fields = re.split(r'[,\n]', self._label)
        node_type, node_id = fields[0].split(" ID: ")
        node_id = int(node_id)
        return node_type, node_id

    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    def __getitem__(self, index) -> Edge:
        return self._edges[index]

    def __iter__(self):
        yield from self._edges

    def __repr__(self) -> str:
        return f'{self._type}(id={self._id}, name={self._name})'


class Graph:
    def __init__(self, nodes: Dict[str, Node] = None, edges: List[Edge] = None) -> None:
        self._nodes = nodes if nodes is not None else {}
        self._edges = edges if edges is not None else []

    @classmethod
    def from_dot_file(cls, dot_file: str) -> Graph:

        nodes: Dict[str, Node] = {}
        edges: List[Edge] = []

        # Regular expressions to match nodes and edges
        node_re = re.compile(r'(Node0x[0-9a-f]+) \[.*label="\{(.+)\}"\];')
        edge_re = re.compile(r'(Node0x[0-9a-f]+) -> (Node0x[0-9a-f]+)\[.*\];')

        # Read the file and split into lines
        with open(dot_file, 'r') as file:
            for line in file:
                line = line.strip()

                # Check if the line contains a node description
                node_match = node_re.match(line)
                if node_match:
                    node_name = node_match.group(1)
                    node_label = node_match.group(2)
                    nodes[node_name] = Node(node_name, node_label)

                # Check if the line contains an edge description
                edge_match = edge_re.match(line)
                if edge_match:
                    source_node = edge_match.group(1)
                    target_node = edge_match.group(2)
                    edge = Edge(source_node, target_node)
                    edges.append(edge)

        for edge in edges:
            nodes[edge.source].add_edge(edge)
            nodes[edge.target].add_edge(edge)

        return cls(nodes, edges)

    def get_name_from_id(self, id: int) -> str:
        """
        Convert node ID to node name
        """
        for node in self:
            if node.id == id:
                return node.name
        else:
            raise ValueError(f"No node found with ID {id}")

    def get_subgraph(self, node_name_or_id: Union[str, int]) -> Graph:
        """
        Get all nodes connected to the given node.

        :return: A Graph object containing nodes connected to the given node.
        """
        if isinstance(node_name_or_id, int):
            node_name = self.get_name_from_id(node_name_or_id)

        visited: Set[Node] = set()

        def _dfs(node_name: str) -> None:
            """
            Depth-First Search helper function.

            :param node_name: The name of the current node.
            :param direction: 'source' or 'target' to control the direction of the search.
            :param visited: Set of visited nodes.
            """
            # Mark the current node as visited
            current_node = self._nodes[node_name]
            visited.add(current_node)

            # Recur for all connected nodes
            for edge in current_node:
                if edge.source == node_name and self._nodes[edge.target] not in visited:
                    _dfs(edge.target)
                elif edge.target == node_name and self._nodes[edge.source] not in visited:
                    _dfs(edge.source)

        _dfs(node_name)
        visited_nodes = {node.name: node for node in visited}
        visited_edges = [edge for edge in self._edges if edge.source in visited_nodes or edge.target in visited_nodes]

        return Graph(visited_nodes, visited_edges)

    def write(self, output_file: str, label=None) -> None:
        """
        Write the graph to a DOT file.

        :param output_file: The name of the output DOT file.
        """
        # Open the output file for writing
        with open(output_file, 'w') as file:
            file.write('digraph G {\n')
            file.write('\trankdir="LR";\n')
            file.write(f'\tlabel="{label}";\n\n')

            # Write nodes
            for node in self._nodes.values():
                file.write(f'\t{node.name} [shape=record,penwidth=2,label="{{{node.label}}}"];\n')

            # Write edges
            for edge in self._edges:
                file.write(f'\t{edge.source} -> {edge.target};\n')

            file.write('}\n')

    def __getitem__(self, node_name: str) -> Node:
        return self._nodes[node_name]

    def __iter__(self) -> Iterator[Node]:
        yield from self._nodes.values()


class Model:
    def __init__(self, vfg: Graph, subvfg: Graph) -> None:
        self._vfg = vfg
        self._subvfg = subvfg


if __name__ == "__main__":
    vfg = Graph.from_dot_file('examples/example0/vfg.dot')
    node_id = 16
    subvfg = vfg.get_subgraph(node_id)
    subvfg.write("examples/example0/subvfg.dot")
