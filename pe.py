from __future__ import annotations
import re
from typing import Set, Dict, List, Tuple, Union, Optional
import copy


class VFGNode:
    def __init__(self, name: str, label: str):
        self.name = name
        self.label = label
        self._type, self._id, self._pag_edge, self._info, self._other = self.parse_label(label)
        self.edges: List[Edge] = []

    @property
    def label(self) -> str:
        return self._label

    @property
    def type(self) -> str:
        return self._type

    @property
    def id(self) -> int:
        return self._id

    @property
    def pag_edge(self) -> str:
        return self._pag_edge

    @property
    def info(self) -> Optional[str]:
        return self._info

    @property
    def other(self) -> Optional[str]:
        return self._other

    def parse_label(self, label: str) -> Tuple[str, int, str, Optional[str], Optional[str]]:
        fields = label.split(',\\n')
        node_type, node_id = fields[0].split(" ID: ")
        node_id = int(node_id)
        pag_edge = fields[1].strip()
        info = fields[2].strip() if len(fields) > 2 else None
        other = fields[3].strip() if len(fields) > 3 else None
        return node_type, node_id, pag_edge, info, other

    def __repr__(self) -> str:
        return f"Node(id='{self.id}', type='{self.type}', name='{self.name}', pag_edge='{self.pag_edge}', info='{self.info}', other='{self.other}')"


class Edge:
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target


class Graph:
    def __init__(self, nodes: Dict[str, VFGNode] = None, edges: List[Edge] = None) -> None:
        self.nodes = nodes if nodes is not None else {}
        self.edges = edges if edges is not None else []

    @classmethod
    def from_dot_file(cls, dot_file: str) -> Graph:
        nodes: Dict[str, VFGNode] = {}
        edges: List[Edge] = []

        # Regular expressions to match nodes and edges
        node_re = re.compile(r'(Node0x\S+)\s+\[.*label="\{(.+)\}"\];')
        edge_re = re.compile(r'(Node0x\S+)\s+->\s+(Node0x[0-9a-f]+)\[.*\];')

        # Read the file and split into lines
        with open(dot_file, 'r') as file:
            lines = file.readlines()

        # Process each line
        for line in lines:
            line = line.strip()

            # Check if the line contains a node description
            node_match = node_re.match(line)
            if node_match:
                node_name = node_match.group(1)
                node_label = node_match.group(2)
                nodes[node_name] = VFGNode(node_name, node_label)

            # Check if the line contains an edge description
            edge_match = edge_re.match(line)
            if edge_match:
                from_node = edge_match.group(1)
                to_node = edge_match.group(2)
                edge = Edge(from_node, to_node)
                edges.append(edge)

                # Add the edge to the source node
                nodes[from_node].edges.append(edge)

        return cls(nodes, edges)

    def add_node(self, node_name: str, label: str) -> None:
        """
        Adds a new node to the graph.

        :param node_name: The name of the node.
        :param label: The label of the node.
        """
        if node_name in self.nodes:
            print(f"A node with the name {node_name} already exists.")
        else:
            self.nodes[node_name] = VFGNode(node_name, label)

    def add_edge(self, from_node: str, to_node: str) -> None:
        """
        Adds a new edge to the graph.

        :param from_node: The name of the source node.
        :param to_node: The name of the target node.
        """
        if from_node not in self.nodes or to_node not in self.nodes:
            print("One or both of the nodes do not exist in the graph.")
        else:
            edge = Edge(from_node, to_node)
            self.edges.append(edge)
            self.nodes[from_node].edges.append(edge)

    def get_subgraph(self, node_name_or_id: Union[str, int]) -> Graph:
        """
        Get all nodes connected to the given node.

        :param node_name_or_id: The name or ID of the node.
        :return: A Graph object containing nodes connected to the given node.
        """
        if isinstance(node_name_or_id, int):
            # Convert node ID to node name
            for node in self.nodes.values():
                if node.id == node_name_or_id:
                    node_name = node.name
                    break
            else:
                print(f"No node found with ID {node_name_or_id}")
                return Graph.from_nodes_and_edges({}, [])
        else:
            node_name = node_name_or_id

        source_visited = set()
        self._dfs(node_name, 'source', source_visited)
        target_visited = set()
        self._dfs(node_name, 'target', target_visited)

        # Get the nodes and edges for the subgraph
        visited_nodes = {node.name: node for node in source_visited | target_visited}
        visited_edges = [edge for edge in self.edges if edge.source in visited_nodes or edge.target in visited_nodes]

        # Return a new Graph object with the connected nodes and edges
        return Graph(visited_nodes, visited_edges)

    def _dfs(self, node_name: str, direction: str, visited: Set[VFGNode]) -> None:
        """
        Depth-First Search helper function.

        :param node_name: The name of the current node.
        :param direction: 'source' or 'target' to control the direction of the search.
        :param visited: Set of visited nodes.
        """
        # Mark the current node as visited
        current_node = self.nodes[node_name]
        visited.add(current_node)

        # Recur for all connected nodes
        for edge in self.edges:
            # Check if it's an outgoing edge
            if direction == 'source' and edge.source == node_name and self.nodes[edge.target] not in visited:
                self._dfs(edge.target, 'source', visited)
            # Check if it's an incoming edge
            elif direction == 'target' and edge.target == node_name and self.nodes[edge.source] not in visited:
                self._dfs(edge.source, 'target', visited)

    def duplicate(self) -> Graph:
        """
        Create a deep copy of the graph.

        :return: A deep copy of the Graph object.
        """
        return copy.deepcopy(self)

    def has_incoming_edges(self, node_name: str) -> bool:
        """
        Check if a node has any incoming edges.

        :param node_name: The name of the node.
        :return: True if the node has incoming edges, False otherwise.
        """
        return any(edge.target == node_name for edge in self.edges)

    def write(self, output_file: str, label=None) -> None:
        """
        Write the graph to a DOT file.

        :param output_file: The name of the output DOT file.
        """
        node_names = {node.name for node in self.nodes.values()}

        # Open the output file for writing
        with open(output_file, 'w') as file:
            file.write('digraph G {\n')
            file.write('	rankdir="LR";\n')
            file.write(f'	label="{label}";\n')

            # Write nodes
            for node in self.nodes.values():
                file.write(f'    {node.name} [shape=record,penwidth=2,label="{{{node.label}}}"];\n')

            # Write edges
            for edge in self.edges:
                if edge.source in node_names and edge.target in node_names:
                    file.write(f'    {edge.source} -> {edge.target};\n')

            file.write('}\n')


class Model:

    binary_operators: Dict[str, str] = {
        'fmul': r'(%\S+) = fmul double (%\S+), (%\S+)'
    }

    def __init__(self, vfg: Graph) -> None:
        self.graph = vfg.duplicate()
        self._opt()

    def _opt(self):
        for node_name in self.graph.nodes:
            node = self.graph.nodes[node_name]
            match node.type:
                case 'AddrVFGNode':
                    node.label = node.info.strip('`')
                case 'LoadVFGNode':
                    node.label = node.info.split(' in ')[0].strip('`').split(' = ')[0]
                case 'CopyVFGNode':
                    node.label = node.info.split(' in ')[0].strip('`').split(' = ')[0]
                case 'ActualRetVFGNode':
                    node.label = node.info.split(' in ')[0].strip('`').split(' = ')[0]
                case 'ActualParmVFGNode':
                    arg_pattern = re.compile(r'Argument `(%\S+)`\s+')
                    arg_match = arg_pattern.match(node.info)
                    if arg_match:
                        node.label = arg_match.group(1)
                    else:
                        node.label = node.info.split(' in ')[0].strip('`').split(' = ')[0]
                case 'FormalParmVFGNode':
                    pattern = re.compile(r'Argument `(%\S+)`\s+')
                    arg_match = pattern.match(node.info)
                    if arg_match:
                        node.label = arg_match.group(1)
                case 'BinaryOPVFGNode':
                    ir = node.info.split(' in ')[0].strip('`')
                    if re.search('fmul', node.info):
                        pattern = re.compile(Model.binary_operators['fmul'])
                        match = pattern.search(ir)
                        if match:
                            node.label = f'{match.group(1)} = fmul({match.group(2)}, {match.group(3)})'
                case 'ActualRetVFGNode':
                        pattern = re.compile(r'(%\S+) = call double (@\S+)\((.*?)%\S+(?:, (.*?)%\S+)*\)')
                        if match:
                            params = []
                            retval = match.group(1)
                            func_name = match.group(2)
                            for param in match.groups()[2:]:
                                if param:
                                    params.append(param)
                        node.label = f"{retval} = {func_name}({params.join(',')})"

    def write(self, output_file: str) -> None:
        self.graph.write(output_file, label="Model")


if __name__ == "__main__":

    graph = Graph.from_dot_file('examples/example0/vfg.dot')  # Replace with the path to your DOT file

    # Get connected nodes for a specific node
    node_name = "Node0x55aefd357cf0"
    node_id = 16
    subgraph = graph.get_subgraph(node_id)

    print(f"\nNodes connected to {node_name}:")
    for node_name in subgraph.nodes:
        print(subgraph.nodes[node_name])

    subgraph.write("subgraph.dot")
