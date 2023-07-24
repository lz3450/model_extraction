from __future__ import annotations
from sys import setrecursionlimit
from typing import Optional, Iterator
import re
from copy import deepcopy
from functools import reduce
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

    def reverse(self):
        self._source, self._target = self._target, self._source

    def __repr__(self) -> str:
        return f'Edge({self._source} → {self._target})'


class Node:
    def __init__(self, name: str, info: str):
        self._name = name
        self._label = info if info else ''
        self._info = re.split(r',\\n\s*', info)
        self._edges: set[Edge] = set()
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
    def ir(self) -> Optional[str]:
        return self._ir

    @property
    def function(self) -> Optional[str]:
        if self._ir:
            pattern = re.compile(r'Function\[(\S+)\]')
            match = pattern.search(self._ir)
            if match:
                return match.group(1)
        return None

    @property
    def basic_block(self) -> Optional[str]:
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

    @property
    def upper_node_names(self) -> Iterator[str]:
        for edge in self._edges:
            if edge.target == self.name:
                yield edge.source

    @property
    def lower_node_names(self) -> Iterator[str]:
        for edge in self._edges:
            if edge.source == self.name:
                yield edge.target

    @property
    def upper_node_number(self) -> int:
        return sum(1 for _ in self.upper_node_names)

    @property
    def lower_node_number(self) -> int:
        return sum(1 for _ in self.lower_node_names)

    @property
    def is_unreachable(self) -> bool:
        return len(self._edges) == 0

    def has_edge(self, source: str, target: str) -> bool:
        for edge in self._edges:
            if edge.source == source and edge.target == target:
                return True
        else:
            return False

    def add_edge(self, edge: Edge) -> None:
        self._edges.add(edge)

    def remove_edge(self, edge: Edge) -> None:
        self._edges.remove(edge)

    def __iter__(self):
        yield from self._edges

    def __repr__(self) -> str:
        return f'{self._type}({self._id}, "{self._name}")'


class Graph:
    logger = logging.getLogger(__qualname__)
    config_logger(logger)

    def __init__(self, nodes: Optional[dict[str, Node]] = None, edges: Optional[set[Edge]] = None) -> None:
        self._nodes = nodes if nodes is not None else dict()
        self._edges = edges if edges is not None else set()

    @classmethod
    def from_dot_file(cls, dot_file: str) -> Graph:

        nodes: dict[str, Node] = dict()
        edges: set[Edge] = set()

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

    def add_node(self, node_name: str, info: str) -> None:
        """
        Adds a new node to the graph.

        :param node_name: The name of the node.
        :param label: The label of the node.
        """
        if node_name in self._nodes:
            print(f"A node with the name {node_name} already exists.")
        else:
            self._nodes[node_name] = Node(node_name, info)

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

    def has_node_name(self, node_name) -> bool:
        return node_name in self._nodes

    def remove_edge(self, edge: Edge) -> None:
        """
        Remove an edge from the graph and the corresponding nodes.
        """
        self._edges.remove(edge)
        if self.has_node_name(edge.source):
            self._nodes[edge.source].remove_edge(edge)
        if self.has_node_name(edge.target):
            self._nodes[edge.target].remove_edge(edge)

    def disconnect_node(self, node_name: str) -> None:
        """
        Remove all edges of the give node.
        """
        for edge in [_ for _ in self._nodes[node_name]]:
            self.remove_edge(edge)

    def remove_node(self, node_name: str) -> None:
        self.disconnect_node(node_name)
        del self._nodes[node_name]

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

    def get_subgraph(self, node_ids: list[int]) -> Graph:
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
            self.logger.debug("Get subgraph from %d", node_id)
            node_name = self.get_name_from_id(node_id)
            _dfs(node_name, 'f')
            _dfs(node_name, 'b')

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
        visited_edges = {edge for edge in self._edges if edge.source in visited_nodes or edge.target in visited_nodes}

        return Graph(visited_nodes, visited_edges)

    def search_nodes(self, type: str, function: str, basic_block: str) -> set[Node]:
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
                # file.write(f'\t{node.name} [shape=record,penwidth=2,label="{{{node.label}}}"];\n')
                file.write(f'\t{node.name} [shape=record,penwidth=2,label="{{{node.type} ID: {node.id}\\n{node.label}}}"];\n')

            # Write edges
            for edge in self._edges:
                file.write(f'\t{edge.source} -> {edge.target};\n')

            file.write('}\n')

    def __len__(self):
        return len(self._nodes)

    def __getitem__(self, node_name: str) -> Node:
        return self._nodes[node_name]

    def __iter__(self) -> Iterator[Node]:
        yield from sorted(self._nodes.values(), key=lambda node: node.id)


class Model:
    logger = logging.getLogger(__qualname__)
    config_logger(logger)

    def __init__(self, vfg: Graph, node_ids: list[int]) -> None:
        self._vfg = vfg
        self._model, self._subvfg = self._vfg_to_model(node_ids)
        self._opt0()
        self._opt1()
        self._opt2()
        self._remove_unreachable_nodes()

    def _vfg_to_model(self, node_ids: list[int]) -> tuple[Graph, Graph]:
        """
        VFG node label to model node label
        """
        def _transform_node(node: Node):
            vfg_updated = False
            if node.ir is None:
                return
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
                    pattern = re.compile(r'(%\S+) = (sitofp|fpext|bitcast|fptrunc) .+ (%\S+) to .+,')
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
                        if node.function is None or node.basic_block is None:
                            self.logger.warning('ActualParmVFGNode (%d) does not contains necessary information', node.id)
                            return
                        callsite_nodes = self._vfg.search_nodes('ActualRetVFGNode', node.function, node.basic_block)
                        for callsite_node in callsite_nodes:
                            if callsite_node.ir is None:
                                self.logger.warning('ActualRetVFGNode (%d) does not contains necessary information', callsite_node.id)
                                return
                            if match.group(1) in callsite_node.ir and not node.has_edge(node.name, callsite_node.name):
                                self._vfg.add_edge(Edge(node.name, callsite_node.name))
                                vfg_updated = True
                                self.logger.debug("VFG updated when processing ActualParmVFGNode (%d)", node.id)
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
                        if node.function is None or node.basic_block is None:
                            self.logger.warning('ActualRetVFGNode (%d) does not contains necessary information', node.id)
                            return
                        param_nodes = self._vfg.search_nodes('ActualParmVFGNode', node.function, node.basic_block)
                        for param_node in param_nodes:
                            for param_label in param_labels:
                                if param_label in param_node.ir and not node.has_edge(param_node.name, node.name):
                                    self._vfg.add_edge(Edge(param_node.name, node.name))
                                    vfg_updated = True
                                    self.logger.debug("VFG updated when processing ActualRetVFGNode (%d)", node.id)
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
                    assert node.upper_node_number == 1
                    pattern = re.compile(r'(%\S+) = getelementptr inbounds (%\S+), (%\S+) (%\S+), (\S+) (\d+), (\S+) (\d+)')
                    match = pattern.match(node.ir)
                    if match:
                        element = match.group(1)
                        ptrvar = match.group(4)
                        node.label = f'{ptrvar}.{element}'
            return vfg_updated

        self.logger.debug("Start to extract model")
        it = 0
        while True:
            it += 1
            self.logger.info("Transform iteration: %d", it)
            subvfg = self._vfg.get_subgraph(node_ids)
            model = subvfg.duplicate()
            self.logger.debug("SUB VFG scale: (node: %d, edge: %d)", subvfg.node_number, subvfg.edge_number)
            for i, node in enumerate(model):
                self.logger.debug("Transforming %d/%d", i + 1, subvfg.node_number)
                if _transform_node(node):
                    break
            else:
                break
        return model, subvfg

    def _opt0(self):
        """
        Pass 0: Remove single-connected edges.
        """
        edge_to_del = [edge for node in self._model for edge in node if not self._model.has_node_name(edge.target) or not self._model.has_node_name(edge.source)]
        for edge in edge_to_del:
            self._model.remove_edge(edge)

    def _opt1(self):
        """
        Pass 1: Remove 'FormalRetVFGNode' nodes.
        """
        for node in self._model:
            if node.type == 'FormalRetVFGNode':
                for lower_node_name in node.lower_node_names:
                    for upper_node_name in node.upper_node_names:
                        self._model.add_edge(Edge(upper_node_name, lower_node_name))
                self._model.disconnect_node(node.name)

    def _opt2(self):
        """
        Pass 2: Remove unnecessary 'GepVFGNode' nodes.
        """
        for node in self._model:
            if node.type == 'GepVFGNode':
                try:
                    upper_node = self._model[next(node.upper_node_names)]
                except StopIteration:
                    pass
                else:
                    if upper_node.type == 'GepVFGNode':
                        node.label = f'{upper_node.label}.{node.label.split(".")[1]}'
                        upper_upper_node_name = next(upper_node.upper_node_names)
                        self._model.add_edge(Edge(upper_upper_node_name, node.name))
                        self._model.disconnect_node(upper_node.name)

    def _remove_unreachable_nodes(self):
        for node in [node for node in self._model if node.is_unreachable]:
            self._model.remove_node(node.name)

    def write_subvfg(self, output_file: str) -> None:
        self._subvfg.write(output_file, label="Sub VFG")

    def write(self, output_file: str) -> None:
        self._model.write(output_file, label="Model")


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    config_logger(logger)

    setrecursionlimit(10000)

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

    vfg = Graph.from_dot_file('examples/tf2/vfg.dot')
    logger.info("VFG scale: (node: %d, edge: %d)", vfg.node_number, vfg.edge_number)
    svfg = Graph.from_dot_file('examples/tf2/full_svfg.dot')
    logger.info("SVFG scale: (node: %d, edge: %d)", svfg.node_number, svfg.edge_number)
    node_ids = [1503, 77788, 77793]
    logger.info("Starting nodes: %s", node_ids)
    model = Model(vfg, node_ids)
    model.write_subvfg("examples/tf2/subvfg.dot")
    model.write("examples/tf2/model.dot")
