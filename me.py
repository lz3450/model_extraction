from __future__ import annotations
from sys import setrecursionlimit
from typing import Set, Dict, List, Union, Optional, Iterator
import re
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

    def __repr__(self) -> str:
        return f'Edge({self._source} → {self._target})'


class Node:
    def __init__(self, name: str, info: Optional[str] = None):
        self._name = name
        self._label = info if info else ''
        self._info = re.split(r',\\n\s*', info) if info else None
        self._edges: Set[Edge] = set()
        self._type, self._id = self._info[0].split(" ID: ")
        try:
            self._ir = self._info[2] if self._info[2] != '(none)' else None
        except IndexError:
            print(self._type, self._id, self._label)

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def id(self) -> int:
        return int(self._id)

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, label: str):
        self._label = label

    @property
    def ir(self) -> str:
        return self._ir

    @property
    def function(self) -> str:
        if self._ir:
            pattern = re.compile(r'Function\[(\S+)\]')
            match = pattern.search(self._ir)
            if match:
                return match.group(1)
        return None

    @property
    def basic_block(self) -> str:
        if self._ir:
            pattern = re.compile(r'BasicBlock\[(\S+)\]')
            match = pattern.search(self._ir)
            if match:
                return match.group(1)
        return None

    @property
    def edge_number(self) -> int:
        return len(self._edges)

    @property
    def has_incoming_edges(self) -> bool:
        """
        Check if a node has any incoming edges.

        :param node_name: The name of the node.
        :return: True if the node has incoming edges, False otherwise.
        """
        return any(edge.target == self.name for edge in self._edges)

    @property
    def has_outgoing_edges(self) -> bool:
        """
        Check if a node has any incoming edges.

        :param node_name: The name of the node.
        :return: True if the node has incoming edges, False otherwise.
        """
        return any(edge.source == self.name for edge in self._edges)

    def has_edge(self, source:str, target:str) -> bool:
        for edge in self._edges:
            if edge.source == source and edge.target == target:
                return True
        else:
            return False


    def add_edge(self, edge: Edge) -> None:
        self._edges.add(edge)

    def remove_edge(self, edge: Edge) -> None:
        self._edges.remove(edge)

    def __getitem__(self, index) -> Edge:
        return self._edges[index]

    def __iter__(self):
        yield from self._edges

    def __repr__(self) -> str:
        return f'{self._type}({self._id}, "{self._name}")'


class Graph:
    def __init__(self, nodes: Dict[str, Node] = None, edges: Set[Edge] = None) -> None:
        self._nodes = nodes if nodes is not None else dict()
        self._edges = edges if edges is not None else set()

    @classmethod
    def from_dot_file(cls, dot_file: str) -> Graph:

        nodes: Dict[str, Node] = dict()
        edges: Set[Edge] = set()

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
                    node_info = node_match.group(2)
                    nodes[node_name] = Node(node_name, node_info)

                # Check if the line contains an edge description
                edge_match = edge_re.match(line)
                if edge_match:
                    source_node = edge_match.group(1)
                    target_node = edge_match.group(2)
                    edge = Edge(source_node, target_node)
                    edges.add(edge)

        for edge in edges:
            nodes[edge.source].add_edge(edge)
            nodes[edge.target].add_edge(edge)

        return cls(nodes, edges)
    
    @property
    def node_number(self):
        return len(self._nodes)
    
    @property
    def edge_number(self):
        return len(self._edges)

    def add_node(self, node_name: str, info: Optional[str] = None) -> None:
        """
        Adds a new node to the graph.

        :param node_name: The name of the node.
        :param label: The label of the node.
        """
        if node_name in self.nodes:
            print(f"A node with the name {node_name} already exists.")
        else:
            self._nodes[node_name] = Node(node_name, info)

    def remove_node(self, node_name: str) -> None:
        del self._nodes[node_name]

    def add_edge(self, edge: Edge) -> None:
        """
        Adds a new edge to the graph.

        :param from_node: The name of the source node.
        :param to_node: The name of the target node.
        """
        if edge.source not in self._nodes or edge.target not in self._nodes:
            print("One or both of the nodes do not exist in the graph.")
        else:
            self._edges.add(edge)
            self._nodes[edge.source].add_edge(edge)
            self._nodes[edge.target].add_edge(edge)

    def remove_edge(self, edge: Edge) -> None:
        self._edges.remove(edge)
        if self.has_node_name(edge.source):
            self._nodes[edge.source].remove_edge(edge)
        if self.has_node_name(edge.target):
            self._nodes[edge.target].remove_edge(edge)

    def has_node_name(self, node_name) -> bool:
        return node_name in self._nodes

    def get_name_from_id(self, id: int) -> str:
        """
        Convert node ID to node name
        """
        for node in self._nodes.values():
            if node.id == id:
                return node.name
        else:
            raise ValueError(f"No node found with ID {id}")

    def get_id_from_name(self, name: str) -> int:
        """
        Convert node ID to node name
        """
        for node in self._nodes.values():
            if node.name == name:
                return node.id
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

        # def _dfs(node_name: str, direction: str = 'f') -> None:
        #     if direction not in ('f', 'b'):
        #         raise ValueError(f'Unknown direction "{direction}"')

        #     # Mark the current node as visited
        #     current_node = self._nodes[node_name]
        #     visited.add(current_node)

        #     # Recur for all connected nodes
        #     for edge in current_node:
        #         if (
        #                 direction == 'f' and
        #                 edge.source == node_name and
        #                 self._nodes[edge.target] not in visited
        #         ):
        #             _dfs(edge.target, direction)
        #         if (
        #                 direction == 'b' and
        #                 edge.source == node_name and
        #                 self._nodes[edge.source] not in visited
        #         ):
        #             _dfs(edge.source, direction)
        # _dfs(node_name, 'f')
        # _dfs(node_name, 'r')
        def _dfs(node_name: str) -> None:
            # Mark the current node as visited
            current_node = self._nodes[node_name]
            visited.add(current_node)

            # Recur for all connected nodes
            for edge in current_node:
                # if edge.source == node_name and self._nodes[edge.target] not in visited:
                #     _dfs(edge.target)
                if edge.target == node_name and self._nodes[edge.source] not in visited:
                    _dfs(edge.source)

        _dfs(node_name)
        visited_nodes = {node.name: node for node in visited}
        visited_edges = {edge for edge in self._edges if edge.source in visited_nodes or edge.target in visited_nodes}

        return Graph(visited_nodes, visited_edges)

    def search_nodes(self, type: str, function: str, basic_block: str) -> Set[Node]:
        matching_nodes = set()
        for node in self._nodes.values():
            if (
                node.type == type and
                node.function == function and
                node.basic_block == basic_block
            ):
                matching_nodes.add(node)
        return matching_nodes

    def duplicate(self) -> Graph:
        """
        Create a deep copy of the graph.

        :return: A deep copy of the Graph object.
        """
        return deepcopy(self)

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

    def __len__(self):
        return len(self._nodes)

    def __getitem__(self, node_name: str) -> Node:
        return self._nodes[node_name]

    def __iter__(self) -> Iterator[Node]:
        yield from self._nodes.values()


class Model:
    logger = logging.getLogger(__qualname__)
    config_logger(logger)

    def __init__(self, vfg: Graph, node_name_or_id: Union[str, int]) -> None:
        self._vfg = vfg.duplicate()
        self._vfg_updated = True
        self._node_id = node_name_or_id if isinstance(node_name_or_id, int) else vfg.get_id_from_name(node_name_or_id)
        self.logger.debug("Start transform Sub VFG to Model")
        i = 0
        while self._vfg_updated:
            i += 1
            self.logger.debug("Transform iteration: %d", i)
            subvfg = self._vfg.get_subgraph(node_name_or_id)
            model = self._transform(subvfg.duplicate())
            self.logger.debug("# Node in Model: %d", len(model))
        self._subvfg = subvfg
        # self._model = model
        self._model = self._opt(model)

    def _transform(self, subvfg: Graph) -> Graph:
        self._vfg_updated = False
        for node in subvfg:
            match node.type:
                case 'AddrVFGNode':
                    pattern = re.compile(r'(\S+) = .+')
                    match = pattern.match(node.ir)
                    if match:
                        node.label = match.group(1)
                    else:
                        node.label = node.ir
                case 'LoadVFGNode':
                    pattern = re.compile(r'(%\S+) = load .+([%@]\S+),')
                    match = pattern.match(node.ir)
                    if match:
                        node.label = f'{match.group(2)} → {match.group(1)}'
                    else:
                        node.label = node.ir
                case 'StoreVFGNode':
                    pattern = re.compile(r'store \S+ (\S+), \S+ (%\S+),')
                    match = pattern.match(node.ir)
                    if match:
                        node.label = f'{match.group(1)} → {match.group(2)}'
                    else:
                        node.label = node.ir
                case 'CopyVFGNode':
                    pattern = re.compile(r'(%\S+) = (sitofp) .+ (%\S+) to .+,')
                    match = pattern.match(node.ir)
                    if match:
                        node.label = f'{match.group(3)} → {match.group(1)}'
                    else:
                        node.label = node.ir
                case 'FormalParmVFGNode':
                    pattern = re.compile(r'\S+ (%\S+)')
                    match = pattern.match(node.ir)
                    if match:
                        node.label = match.group(1)
                    else:
                        node.label = node.ir
                case 'ActualParmVFGNode':
                    if ' = ' in node.ir:
                        pattern = re.compile(r'(%\S+) = .+')
                    else:
                        pattern = re.compile(r'\S+ (%\S+)')
                    match = pattern.match(node.ir)
                    if match:
                        node.label = match.group(1)
                        callsite_nodes = self._vfg.search_nodes('ActualRetVFGNode', node.function, node.basic_block)
                        for callsite_node in callsite_nodes:
                            if match.group(1) in callsite_node.ir and not node.has_edge(node.name, callsite_node.name):
                                self._vfg.add_edge(Edge(node.name, callsite_node.name))
                                self._vfg_updated = True
                    else:
                        node.label = node.ir
                case 'ActualRetVFGNode':
                    pattern = re.compile(r'(%\S+) = (call|invoke) .+ (@\S+)\((.+)\)')
                    match = pattern.match(node.ir)
                    if match:
                        retval = match.group(1)
                        func_name = match.group(3)
                        params = match.group(4)
                        param_labels = []
                        param_pattern = re.compile(r'.+ (\S+)')
                        for param in params.split(', '):
                            param_match = param_pattern.match(param)
                            if param_match:
                                param_labels.append(param_match.group(1))
                        node.label = f"{retval} = {func_name}({', '.join(param_labels)})"
                        param_nodes = self._vfg.search_nodes('ActualParmVFGNode', node.function, node.basic_block)
                        for param_node in param_nodes:
                            for param_label in param_labels:
                                if param_label in param_node.ir and not node.has_edge(param_node.name, node.name):
                                    self._vfg.add_edge(Edge(param_node.name, node.name))
                                    self._vfg_updated = True
                    else:
                        node.label = node.ir
                case 'BinaryOPVFGNode':
                    pattern = re.compile(r'(%\S+) = (fmul|fadd) .+ (%\S+), (%\S+)')
                    match = pattern.match(node.ir)
                    if match:
                        node.label = f'{match.group(1)} = {match.group(2)}({match.group(3)}, {match.group(4)})'
                    else:
                        node.label = node.ir
                case 'GepVFGNode':
                    pattern = re.compile(r'(%\S+) = getelementptr inbounds (%\S+), (%\S+) (%\S+), (\S+) (\d+), (\S+) (\d+)')
                    match = pattern.match(node.ir)
                    if match:
                        element = match.group(1)
                        ptrvar = match.group(4)
                        node.label = f'{ptrvar}.{element}'
        return subvfg

    def _opt(self, model: Graph):
        edge_to_del = [edge for node in model for edge in node if not model.has_node_name(edge.target) or not model.has_node_name(edge.source)]
        for edge in edge_to_del:
            model.remove_edge(edge)

        node_to_del: List[Node] = []
        for node in model:
            match node.type:
                case 'FormalRetVFGNode':
                    node_to_del.append(node)
                    lower_node_names: List[str] = []
                    upper_node_names: List[str] = []
                    for edge in node:
                        if edge.source == node.name:
                            lower_node_names.append(edge.target)
                        elif edge.target == node.name:
                            upper_node_names.append(edge.source)
                        else:
                            assert False
                    for lower_node_name in lower_node_names:
                        for upper_node_name in upper_node_names:
                            model.add_edge(Edge(upper_node_name, lower_node_name))
        for node in node_to_del:
            edge_to_del = [edge for edge in node]
            model.remove_node(node.name)
        for edge in edge_to_del:
            model.remove_edge(edge)
            # case 'IntraPHIVFGNode':
            #     if node[0].source == node.name:
            #         outgoing_node_name, incoming_node_name = node[0].target, node[1].source if node[0].source == node.name else node[1].target, node[0].source
            #         model.add_edge(Edge(incoming_node_name, outgoing_node_name))
            #         model.remove_edge(node[0])
            #         model.remove_edge(node[1])

        return model

    def write_subvfg(self, output_file: str) -> None:
        self._subvfg.write(output_file, label="Sub VFG")

    def write(self, output_file: str) -> None:
        self._model.write(output_file, label="Model")


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    config_logger(logger)

    setrecursionlimit(5000)


    # vfg = Graph.from_dot_file('examples/example0/vfg.dot')
    # svfg = Graph.from_dot_file('examples/example0/full_svfg.dot')
    # model = Model(vfg, 16)
    # model.write_subvfg("examples/example0/subvfg.dot")
    # model.write("examples/example0/model.dot")

    # vfg = Graph.from_dot_file('examples/example1/vfg.dot')
    # svfg = Graph.from_dot_file('examples/example1/full_svfg.dot')
    # model = Model(vfg, 42)
    # model.write_subvfg("examples/example1/subvfg.dot")
    # model.write("examples/example1/model.dot")

    vfg = Graph.from_dot_file('tmp/vfg.dot')
    logger.info("VFG scale: (node: %d, edge: %d)", vfg.node_number, vfg.edge_number)
    # svfg = Graph.from_dot_file('tmp/full_svfg.dot')
    node_id = 77793
    # model = Model(vfg, 77788)
    # model = Model(vfg, 1503)
    logger.info("Starting node: %s", vfg[vfg.get_name_from_id(node_id)])
    model = Model(vfg, node_id)
    model.write_subvfg("tmp/subvfg.dot")
    model.write("tmp/model.dot")
