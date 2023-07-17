from __future__ import annotations
from typing import Set, Dict, List, Tuple, Union, Optional
import re
import functools
from copy import deepcopy
import logging


def config_logger(logger: logging.Logger):
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)


class Node:
    def __init__(self, name: str, label: str):
        self.name = name
        self.label = label
        self._type, self._id, self._pag_edge, self._info, self._other = self.parse_label(label)
        self.edges: List[Edge] = []

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

    @property
    def ir(self) -> Optional[str]:
        return self.info.split(' in ')[0].strip('`') if self._info is not None else None

    @property
    def function(self) -> Optional[str]:
        if self.info:
            match = re.search(r'in \[(\S+)\] BB', self.info)
            if match:
                return match.group(1)
        return None

    @property
    def basic_block(self) -> Optional[str]:
        if self.info:
            match = re.search(r'BB `(\S+)`', self.info)
            if match:
                return match.group(1)
        return None

    def parse_label(self, label: str) -> Tuple[str, int, str, Optional[str], Optional[str]]:
        fields = label.split(r',\n')
        try:
            node_type, node_id = fields[0].split(" ID: ")
        except ValueError:
            print(fields)
            exit(1)
        try:
            node_id = int(node_id)
        except ValueError:
            print(fields)
            exit(1)
        pag_edge = fields[1].strip()
        info = fields[2].strip() if len(fields) > 2 else None
        other = fields[3].strip() if len(fields) > 3 else None
        return node_type, node_id, pag_edge, info, other

    def __str__(self) -> str:
        return f"Node(id='{self.id}', type='{self.type}', name='{self.name}', ir='{self.ir}', func='{self.function}', BB='{self.basic_block}')"

    def __repr__(self) -> str:
        return f"Node(id='{self.id}', type='{self.type}', name='{self.name}', pag_edge='{self.pag_edge}', info='{self.info}', other='{self.other}')"


class Edge:
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target


class Graph:
    logger = logging.getLogger(__qualname__)
    # config_logger(logger)

    def __init__(self, nodes: Dict[str, Node] = None, edges: List[Edge] = None) -> None:
        self.nodes = nodes if nodes is not None else {}
        self.edges = edges if edges is not None else []

        self.logger = logging.getLogger(__name__)
        config_logger(self.logger)

    @classmethod
    def from_dot_file(cls, dot_file: str) -> Graph:

        cls.logger.info(f'Building graph from dot file "{dot_file}"')

        nodes: Dict[str, Node] = {}
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
                nodes[node_name] = Node(node_name, node_label)

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
            self.nodes[node_name] = Node(node_name, label)

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

    def duplicate(self) -> Graph:
        """
        Create a deep copy of the graph.

        :return: A deep copy of the Graph object.
        """
        return deepcopy(self)

    def has_incoming_edges(self, node_name: str) -> bool:
        """
        Check if a node has any incoming edges.

        :param node_name: The name of the node.
        :return: True if the node has incoming edges, False otherwise.
        """
        return any(edge.target == node_name for edge in self.edges)

    def search_nodes(self, type: str, label: str, function: str, basic_block: str) -> Set[Node]:
        matching_nodes = set()
        for node in self.nodes.values():
            if (
                node.type == type and
                node.function == function and
                node.basic_block == basic_block and
                re.search(f'{label} = ', node.ir)
            ):
                matching_nodes.add(node)
        return matching_nodes

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
    logger = logging.getLogger(__qualname__)
    config_logger(logger)

    binary_operators: Dict[str, str] = {
        'fmul': r'(%\S+) = fmul double (%\S+), (%\S+)',
        'fadd': r'(%\S+) = fadd double (%\S+), (%\S+)'
    }

    def __init__(self, vfg: Graph, node_name_or_id: Union[str, int]) -> None:
        self.vfg = vfg

        if isinstance(node_name_or_id, int):
            # Convert node ID to node name
            for node in self.vfg.nodes.values():
                if node.id == node_name_or_id:
                    self._node_name = node.name
                    break
            else:
                raise ValueError(f"No node found with ID {node_name_or_id}")
        else:
            self._node_name = node_name_or_id

        self._extract_model()

    @property
    def node_name(self) -> str:
        return self._node_name

    def _extract_model(self):
        self.subvfg = self.get_subvfg()
        self.model = self.subvfg.duplicate()
        self._extract()

    def _extract(self):
        for node_name in self.model.nodes:
            node = self.model.nodes[node_name]
            match node.type:
                case 'AddrVFGNode':
                    alloca_pattern = re.compile(r'(\S+) = alloca (.+)')
                    match = alloca_pattern.search(node.ir)
                    if match:
                        node.label = match.group(1)
                    else:
                        node.label = node.ir
                case 'LoadVFGNode':
                    node.label = node.ir.split(' = ')[0]
                case 'StoreVFGNode':
                    store_pattern = re.compile(r'store \S+ (%\S+), \S+ (%\S+),')
                    match = store_pattern.search(node.ir)
                    if match:
                        node.label = f'{match.group(1)} → {match.group(2)}'
                    else:
                        node.label = node.ir
                case 'CopyVFGNode':
                    node.label = node.ir.split(' = ')[0]
                case 'ActualParmVFGNode':
                    arg_pattern = re.compile(r'Argument `(%\S+)`\s+')
                    arg_match = arg_pattern.match(node.info)
                    if arg_match:
                        node.label = arg_match.group(1)
                    else:
                        node.label = node.ir.split(' = ')[0]
                case 'FormalParmVFGNode':
                    pattern = re.compile(r'Argument `(%\S+)`\s+')
                    arg_match = pattern.match(node.info)
                    if arg_match:
                        node.label = arg_match.group(1)
                case 'BinaryOPVFGNode':
                    if re.search('fmul', node.ir):
                        pattern = re.compile(Model.binary_operators['fmul'])
                        match = pattern.search(node.ir)
                        if match:
                            node.label = f'{match.group(1)} = fmul({match.group(2)}, {match.group(3)})'
                        else:
                            node.label = node.ir
                    elif re.search('fadd', node.ir):
                        pattern = re.compile(Model.binary_operators['fadd'])
                        match = pattern.search(node.ir)
                        if match:
                            node.label = f'{match.group(1)} = fmul({match.group(2)}, {match.group(3)})'
                        else:
                            node.label = node.ir
                case 'GepVFGNode':
                    pattern = re.compile(r'(%\S+) = getelementptr inbounds (%\S+), (%\S+) (%\S+), (\S+) (\d+), (\S+) (\d+)')
                    match = pattern.search(node.ir)
                    if match:
                        element = match.group(1)
                        ptrvar = match.group(4)
                        node.label = f'{ptrvar}.{element}'
                case 'ActualRetVFGNode':
                    pattern = re.compile(r'(%\S+) = call (\S+) (@\S+)\((.+)\)')
                    param_pattern = re.compile(r'(.+) (%\S+)')
                    match = pattern.search(node.ir)
                    if match:
                        retval = match.group(1)
                        func_name = match.group(3)
                        params = match.group(4)
                        param_labels = []
                        for param in params.split(', '):
                            param_match = param_pattern.search(param)
                            if param_match:
                                param_labels.append(param_match.group(2))
                        node.label = f"{retval} = {func_name}({', '.join(param_labels)})"
                        if not self.vfg.has_incoming_edges(node.name):
                            param_nodes = functools.reduce(lambda a, b: a | b, [self.vfg.search_nodes('ActualParmVFGNode', label, node.function, node.basic_block) for label in param_labels])
                            for param_node in param_nodes:
                                self.vfg.add_edge(param_node.name, node.name)
                            self._extract_model()
                case 'FormalINSVFGNode':
                    node.label = node.ir
                case 'FormalOUTSVFGNode':
                    node.label = node.ir
                case 'ActualINSVFGNode':
                    node.label = node.ir
                case 'ActualOUTSVFGNode':
                    node.label = node.ir
                case 'IntraPHIVFGNode':
                    node.label = node.ir
                case 'BranchVFGNode':
                    node.label = node.ir
                case 'FormalRetVFGNode':
                    node.label = node.ir
                case 'CmpVFGNode':
                    node.label = node.ir
                case 'NullPtrVFGNode':
                    node.label = node.ir
                case _:
                    raise ValueError(f'Unknown VFG node type "{node.type}".')

    def _dfs(self, node_name: str, direction: str, visited: Set[Node]) -> None:
        """
        Depth-First Search helper function.

        :param node_name: The name of the current node.
        :param direction: 'source' or 'target' to control the direction of the search.
        :param visited: Set of visited nodes.
        """
        # Mark the current node as visited
        current_node = self.vfg.nodes[node_name]
        visited.add(current_node)

        # Recur for all connected nodes
        for edge in self.vfg.edges:
            # Check if it's an outgoing edge
            if direction == 'source' and edge.source == node_name and self.vfg.nodes[edge.target] not in visited:
                self._dfs(edge.target, 'source', visited)
            # Check if it's an incoming edge
            elif direction == 'target' and edge.target == node_name and self.vfg.nodes[edge.source] not in visited:
                self._dfs(edge.source, 'target', visited)

    def _bfs(self, node_name: str) -> Set[Node]:
        current_node = self.vfg.nodes[node_name]
        all_visited = {current_node}

        pass_num = 1
        last_visited = all_visited
        while True:
            new_visited = set()
            node_num = len(all_visited)
            self.logger.debug('Pass: %3d\t#Node: %6d', pass_num, node_num)
            for node in last_visited:
                for edge in self.vfg.edges:
                    if edge.source == node.name:
                        new_visited.add(self.vfg.nodes[edge.target])
                    elif edge.target == node.name:
                        new_visited.add(self.vfg.nodes[edge.source])
            all_visited = all_visited | new_visited
            last_visited = new_visited
            if len(all_visited) - node_num == 0:
                break
            if pass_num >= 10:
                break
            pass_num += 1

        return all_visited

    def get_subvfg(self) -> Graph:
        """
        Get all nodes connected to the given node.

        :return: A Graph object containing nodes connected to the given node.
        """
        # source_visited: Set[VFGNode] = set()
        # self._dfs(self._node_name, 'source', source_visited)
        # target_visited: Set[VFGNode] = set()
        # self._dfs(self._node_name, 'target', target_visited)

        # # Get the nodes and edges for the subgraph
        # visited_nodes = {node.name: node for node in (source_visited | target_visited)}
        # visited_edges = [edge for edge in self.vfg.edges if edge.source in visited_nodes or edge.target in visited_nodes]

        visited = self._bfs(self._node_name)
        visited_nodes = {node.name: node  for node in visited}
        visited_edges = [edge for edge in self.vfg.edges if edge.source in visited_nodes or edge.target in visited_nodes]

        # Return a new Graph object with the connected nodes and edges
        return Graph(visited_nodes, visited_edges)

    def write_subvfg(self, output_file: str) -> None:
        self.subvfg.write(output_file, label="Sub VFG")

    def write(self, output_file: str) -> None:
        self.model.write(output_file, label="Model")


if __name__ == "__main__":
    # graph = Graph.from_dot_file('examples/example0/vfg.dot')
    # node_name = "Node0x55aefd357cf0"
    # node_id = 16
    # subgraph = graph.get_subgraph(node_id)
    # subgraph.write("examples/example0/subgraph.dot")
    # m = Model(subgraph)
    # m.write("examples/example0/model.dot")

    # vfg = Graph.from_dot_file('examples/example1/vfg.dot')
    # node_id = 42
    # m = Model(vfg, node_id)
    # m.write_subvfg('examples/example1/subvfg.dot')
    # m.write('examples/example1/model.dot')

    vfg = Graph.from_dot_file('tmp/vfg.dot')
    # node_name = 'Node0x5631daa31250'
    # node_id = 55971
    node_id = 77788
    # node_id = 1508
    m = Model(vfg, node_id)
    m.write_subvfg('tmp/subvfg.dot')
    m.write("tmp/model.dot")
