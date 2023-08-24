from __future__ import annotations
from typing import Iterator
import re
import logging

from .log import config_logger

from .vfg_edge import VFGEdge
from .vfg_node import VFGNode


logger = logging.getLogger(__name__)
config_logger(logger)


class VFG:
    def __init__(self, nodes: dict[str, VFGNode], edges: set[VFGEdge]) -> None:
        self._nodes = nodes
        self._edges = edges
        self._changed = False

    @property
    def node_number(self) -> int:
        return len(self._nodes)

    @property
    def edge_number(self) -> int:
        return len(self._edges)

    @property
    def nodes(self) -> Iterator[VFGNode]:
        yield from sorted(self._nodes.values(), key=lambda node: node.id)

    @property
    def edges(self) -> Iterator[VFGEdge]:
        yield from self._edges

    @property
    def changed(self) -> bool:
        if self._changed:
            self._changed = False
            return True
        return False

    @changed.setter
    def changed(self, value: bool):
        self._changed = bool(value)

    def add_node(self, node_name: str, info: str) -> None:
        """
        Adds a new node to the graph.

        :param node_name: The name of the node.
        :param label: The label of the node.
        """
        if node_name in self._nodes:
            logger.warning("A node with the name %s already exists.", node_name)
        else:
            self._nodes[node_name] = VFGNode(node_name, info)
            self.changed = True

    def add_edge(self, edge: VFGEdge) -> None:
        """
        Adds a new edge to the graph.

        :param from_node: The name of the source node.
        :param to_node: The name of the target node.
        """
        if edge.source not in self._nodes or edge.target not in self._nodes:
            logger.warning("One or both of the nodes do not exist in the graph.")
        else:
            self._edges.add(edge)
            self._nodes[edge.source].add_edge(edge)
            self._nodes[edge.target].add_edge(edge)
            self.changed = True

    def disconnect_node(self, node_name: str) -> None:
        """
        Remove all edges of the give node.
        """
        for edge in [_ for _ in self._nodes[node_name]]:
            self.remove_edge(edge)

    def remove_node(self, node_name: str) -> None:
        self.disconnect_node(node_name)
        del self._nodes[node_name]
        self.changed = True

    def remove_edge(self, edge: VFGEdge) -> None:
        """
        Remove an edge from the graph and the corresponding nodes.
        """
        self._edges.remove(edge)
        if self.has_node_name(edge.source):
            self._nodes[edge.source].remove_edge(edge)
        if self.has_node_name(edge.target):
            self._nodes[edge.target].remove_edge(edge)
        self.changed = True

    def has_node_name(self, node_name) -> bool:
        return node_name in self._nodes

    def get_name_from_id(self, id: int) -> str:
        """
        Convert node ID to node name.
        """
        for node in self._nodes.values():
            if node.id == id:
                return node.name
        raise ValueError(f"No node found with ID {id}")

    def get_id_from_name(self, name: str) -> int:
        """
        Convert node ID to node name
        """
        for node in self._nodes.values():
            if node.name == name:
                return node.id
        raise ValueError(f"No node found with ID {id}")

    def search_nodes(self, type: str, function: str, basic_block: str) -> set[VFGNode]:
        matching_nodes = set()
        for node in self._nodes.values():
            if (
                node.type == type and
                node.function == function and
                node.basic_block == basic_block
            ):
                matching_nodes.add(node)
        return matching_nodes

    def get_subgraph(self, node_ids: list[int]) -> VFG:
        """
        Get all nodes connected to the given node.
        """
        forward_visited: set[str] = set()
        backward_visited: set[str] = set()

        def _dfs(node_name: str, direction: str = 'f') -> None:
            if direction not in ('f', 'b'):
                raise ValueError(f'Unknown direction "{direction}"')

            # Mark the current node as visited
            current_node_name = node_name
            if direction == 'f':
                forward_visited.add(current_node_name)
            elif direction == 'b':
                backward_visited.add(current_node_name)
            else:
                raise ValueError('Unknown direction')

            current_node = self._nodes[current_node_name]
            # Recur for all connected nodes
            for edge in current_node:
                if (
                        direction == 'f' and
                        edge.source == node_name and
                        edge.target not in forward_visited
                ):
                    _dfs(edge.target, 'f')
                if (
                        direction == 'b' and
                        edge.target == node_name and
                        edge.source not in backward_visited
                ):
                    _dfs(edge.source, 'b')

        for node_id in node_ids:
            logger.debug("Get subgraph from %d", node_id)
            node_name = self.get_name_from_id(node_id)
            _dfs(node_name, 'f')
            _dfs(node_name, 'b')

        # visited: set[str] = set()

        # def _dfs(node_name: str) -> None:
        #     # Mark the current node as visited
        #     current_node_name = node_name
        #     visited.add(current_node_name)

        #     current_node = self._nodes[current_node_name]
        #     # Recur for all connected nodes
        #     for edge in current_node:
        #         if edge.source == node_name and self._nodes[edge.target] not in visited:
        #             _dfs(edge.target)
        #         if edge.target == node_name and self._nodes[edge.source] not in visited:
        #             _dfs(edge.source)
        # for node_id in node_ids:
        #     node_name = self.get_name_from_id(node_id)
        #     _dfs(node_name)

        visited_nodes = {name: self._nodes[name] for name in forward_visited | backward_visited}
        # visited_nodes = {name: self._nodes[name] for name in visited}
        visited_edges = {
            edge for edge in self._edges if edge.source in visited_nodes or edge.target in visited_nodes}

        return VFG(visited_nodes, visited_edges)

    def write(self, output_file: str, label=None) -> None:
        """
        Write the graph to a DOT file.

        :param output_file: The name of the output DOT file.
        """
        # Open the output file for writing
        with open(output_file, mode='w', encoding='utf-8') as file:
            file.write('digraph "VFG" {\n')
            file.write('\trankdir="LR";\n')
            file.write(f'\tlabel="{label}";\n\n')

            # Write nodes
            for node in self._nodes.values():
                # file.write(f'\t{node.name} [shape={node.shape},color={node.color},penwidth=2,label="{{{node.label}}}"];\n')
                file.write(f'\t{node.name} [shape={node.shape},color={node.color},penwidth={node.penwidth},label="{{{node.type} ID: {node.id}\\n{node.label}}}"];\n')

            # Write edges
            for edge in self._edges:
                file.write(f'\t{edge.source} -> {edge.target}[style={edge.style},color={edge.color}];\n')

            file.write("}\n")

    def __len__(self):
        return len(self._nodes)

    def __getitem__(self, node_name: str) -> VFGNode:
        return self._nodes[node_name]

    def __iter__(self) -> Iterator[VFGNode]:
        return self.nodes


def read_vfg(dot_file: str) -> VFG:
    """Read VFG from a ".dot" file."""
    nodes: dict[str, VFGNode] = {}
    edges: set[VFGEdge] = set()

    # Regular expressions to match nodes and edges
    header_re = re.compile(r'digraph.+\{|rankdir=.+|label=.+|\}')
    node_re = re.compile(r'(Node0x[0-9a-f]+) \[shape=(\w+),color=(\w+)(?:,penwidth=(\d+))?,label="\{(.+)\}"\];')
    edge_re = re.compile(r'(Node0x[0-9a-f]+) -> (Node0x[0-9a-f]+)\[style=(\w+)(?:,color=(\w+))?\];')

    # Read the file and split into lines
    with open(dot_file, mode='r', encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            # Check if the line contains a node description
            node_match = node_re.match(line)
            if node_match:
                node_name = node_match[1]
                node_shape = node_match[2]
                node_color = node_match[3]
                node_penwidth = 2 * int(node_match[4]) if node_match[4] else 2
                node_label = node_match[5]
                nodes[node_name] = VFGNode(node_name, node_label, node_shape, node_color, node_penwidth)
                continue

            # Check if the line contains an edge description
            edge_match = edge_re.match(line)
            if edge_match:
                source_node, target_node, style, color = edge_match[1], edge_match[2], edge_match[3], edge_match[4] if edge_match[4] else "black"
                edge = VFGEdge(source_node, target_node, style, color)
                edges.add(edge)
                continue

            header_match = header_re.match(line)
            if header_match:
                continue

            if not line:
                continue

            raise RuntimeWarning(f"Unrecognized line: {line}")

    for edge in edges:
        nodes[edge.source].add_edge(edge)
        nodes[edge.target].add_edge(edge)

    return VFG(nodes, edges)
