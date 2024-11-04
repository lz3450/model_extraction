################################################################################
# VFG Node  -   Attributes
# ADDR      -   {self.var_type} {self.ptr}
# Gep       -   {ptr}.{elementptr}
################################################################################


from __future__ import annotations
from typing import Iterator
import re
import subprocess
from tqdm import tqdm

from .graph import Node, Edge, Graph
from .log import get_logger


logger = get_logger(__name__)

SHORT_TYPE: dict[str, str] = {
    'Addr': 'a',
    'Load': 'l',
    'Store': 's',
    'Gep': 'g',
    'Copy': 'c',
    'FormalParm': ')',
    'ActualParm': '(',
    'FormalRet': '<',
    'ActualRet': '>',
    'BinaryOP': 'b',
    'UnaryOP': 'u',
    'IntraPHI': 'p',
    'Branch': '^',
    'Cmp': '%',
    'NullPtr': 'n',
    'FormalINS': '+',
    'FormalOUTS': '-',
    'ActualINS': 'i',
    'ActualOUTS': 'o',
    'IntraMSSAPHIS': 'm'
}

PATTERNS: dict[str, re.Pattern] = {
    'NodeLabelSeparation': re.compile(r',\\n\s*'),
    'Function': re.compile(r'Function\[(\S+)\]'),
    'BasicBlock': re.compile(r'BasicBlock\[(\S+)\]'),
    'FunctionArgs': re.compile(r'.+ (\S+)'),
    'Addr': re.compile(r'(\S+) = alloca (.+), align .+'),
    'Load': re.compile(r'(%\S+) = load .+([%@]\S+),'),
    'Store': re.compile(r'store \S+ (\S+), \S+ (%\S+),'),
    'Gep': re.compile(r'(%\S+) = getelementptr inbounds (%\S+), (%\S+) (%\S+), (\S+) (\d+), (\S+) (\d+)'),
    'Copy': re.compile(r'(%\S+) = (sitofp|fpext|bitcast|fptrunc) .+ (%\S+) to .+,'),
    'FormalParm': re.compile(r'\S+ (%\S+)'),
    'ActualParm': re.compile(r'(%\S+) = .+|\S+ (%\S+)'),
    'ActualRet': re.compile(r'(%\S+) = (call|invoke) .+ @(\S+)\((.+)\)'),
    'BinaryOP': re.compile(r'(%\S+) = (fmul|fadd) .+ (%\S+), (%\S+),'),
}


class VFGNode:
    def __init__(self, node: Node):
        self.name = node.name
        self.info = PATTERNS['NodeLabelSeparation'].split(node.label.removeprefix('{').removesuffix('}'))
        self.type, self.id = self._get_type_and_id()
        self.t = SHORT_TYPE[self.type]
        self.ir, self.function, self.basic_block = self._get_ir()
        # self.label = f'{self.type}({self.id})\\n{self._compile_info()}'
        self.compiled_info = self._compile_info()
        self.upper_nodes: set[VFGNode] = set()
        self.lower_nodes: set[VFGNode] = set()

    @staticmethod
    def demangle(mangled_name: str) -> str:
        return subprocess.run(['c++filt', '-p', mangled_name], capture_output=True, text=True, check=True).stdout.strip().replace('<', '\\<').replace('>', '\\>')

    def _get_type_and_id(self) -> tuple[str, int]:
        type_and_id = self.info[0].split(" ID: ")
        assert len(type_and_id) == 2, f'Invalid format for VFGNode "{self.name}" type and ID information'
        return type_and_id[0].removesuffix('VFGNode'), int(type_and_id[1])

    def _get_ir(self) -> tuple[str, str, str]:
        ir = self.info[2]
        f = ''
        bb = ''

        if not ir.startswith('(none)'):
            if match := PATTERNS['Function'].search(ir):
                f = VFGNode.demangle(match.group(1))
            if match := PATTERNS['BasicBlock'].search(ir):
                bb = match.group(1)
        elif self.type == 'FormalRet':
            if match := PATTERNS['Function'].search(self.info[1]):
                f = VFGNode.demangle(match.group(1))
        else:
            ir = ''
            if self.type != 'NullPtr':
                logger.warning('%s (%d) does not contains IR code', self.type, self.id)

        return ir, f, bb

    def _compile_info(self) -> str:
        if not self.ir:
            return ''
        match self.type:
            case 'Addr':
                if match := PATTERNS[self.type].match(self.ir):
                    self._var_type = match.group(2)
                    self._ptr = match.group(1)
                    return f"{self._var_type} {self._ptr}"
            case 'Load':
                if match := PATTERNS[self.type].match(self.ir):
                    self._ptr = match.group(2)
                    self._var = match.group(1)
                    return f'{self._ptr} → {self._var}'
            case 'Store':
                if match := PATTERNS[self.type].match(self.ir):
                    self._var = match[1]
                    self._ptr = match[2]
                    return f'{self._var} → {self._ptr}'
            case 'Gep':
                if match := PATTERNS[self.type].match(self.ir):
                    self._elementptr = match.group(1)
                    self._ptr = match.group(4)
                    return f'{self._ptr}.{self._elementptr}'
            case 'Copy':
                if match := PATTERNS[self.type].match(self.ir):
                    self._from_var = match[3]
                    self._to_var = match[1]
                    return f'{self._from_var} → {self._to_var}'
            case 'FormalParm':
                if match := PATTERNS[self.type].match(self.ir):
                    self._parm = match.group(1)
                    return self._parm
            case 'ActualParm':
                if match := PATTERNS[self.type].match(self.ir):
                    group1, group2 = match.groups()
                    self._parm = group1 if group1 else group2
                    return self._parm
            case 'FormalRet':
                return self.function
            case 'ActualRet':
                self._args: list[str] = []
                if match := PATTERNS[self.type].match(self.ir):
                    self._retval = match[1]
                    self._fnptrval = match[3]
                    args = match[4]
                    for arg in args.split(', '):
                        if arg_match := PATTERNS['FunctionArgs'].match(arg):
                            self._args.append(arg_match[1])
                    return f"{self._retval} = {VFGNode.demangle(self._fnptrval)}({', '.join(self._args)})"
            case 'BinaryOP':
                if match := PATTERNS[self.type].match(self.ir):
                    self._binary_op_parms = (match[3], match[4])
                    return f'{match[2]}({", ".join(self._binary_op_parms)}) → {match[1]}'
            case 'UnaryOP':
                pass
            case 'IntraPHI':
                return self.function
            case 'Branch':
                pass
            case 'Cmp':
                pass
            case 'FormalINS':
                pass
            case 'FormalOUTS':
                pass
            case 'ActualINS':
                pass
            case 'ActualOUTS':
                pass
            case 'IntraMSSAPHIS':
                pass
            case _:
                raise ValueError(f'Unknown VFG node type {self.type}')
        return r'\n'.join(self.info)

    def __repr__(self) -> str:
        return f'{self.type}({self.id}, {self.name})'

    @property
    def var_type(self) -> str:
        if self.t != 'a':
            raise AttributeError(f'"{self.type}" does not have `var_type` attribute.')
        return self._var_type

    @property
    def ptr(self) -> str:
        if self.t not in 'alsg':
            raise AttributeError(f'"{self.type}" does not have `ptr` attribute.')
        return self._ptr

    @property
    def var(self) -> str:
        if self.t not in 'ls':
            raise AttributeError(f'"{self.type}" does not have `var` attribute.')
        return self._var

    @property
    def elementptr(self) -> str:
        if self.t != 'g':
            raise AttributeError(f'"{self.type}" does not have `elementptr` attribute.')
        return self._elementptr

    @property
    def from_var(self) -> str:
        if self.t != 'c':
            raise AttributeError(f'"{self.type}" does not have `from_var` attribute.')
        return self._from_var

    @property
    def to_var(self) -> str:
        if self.t != 'c':
            raise AttributeError(f'"{self.type}" does not have `to_var` attribute.')
        return self._to_var

    @property
    def parm(self) -> str:
        if self.t not in '()':
            raise AttributeError(f'"{self.type}" does not have `parm` attribute.')
        return self._parm

    @property
    def parms(self) -> tuple[str, str]:
        if self.t != 'b':
            raise AttributeError(f'"{self.type}" does not have `parms` attribute.')
        return self._binary_op_parms

    @property
    def retval(self) -> str:
        if self.t != '>':
            raise AttributeError(f'"{self.type}" does not have `retval` attribute.')
        return self._retval

    @property
    def args(self) -> list[str]:
        if self.t != '>':
            raise AttributeError(f'"{self.type}" does not have `args` attribute.')
        return self._args

    @property
    def upper_node_number(self) -> int:
        return len(self.upper_nodes)

    @property
    def lower_node_number(self) -> int:
        return len(self.lower_nodes)

    def add_upper_nodes(self, node: VFGNode):
        if node != self:
            self.upper_nodes.add(node)

    def add_lower_nodes(self, node: VFGNode):
        if node != self:
            self.lower_nodes.add(node)


class VFG:
    def __init__(self, graph: Graph) -> None:
        self.nodes: dict[str, VFGNode] = {node.name: VFGNode(node) for node in tqdm(graph.nodes, bar_format='{l_bar}{bar:50}{r_bar}', unit=' nodes')}
        for edge in tqdm(graph.edges, bar_format='{l_bar}{bar:50}{r_bar}', unit=' edges'):
            self.nodes[edge.source].add_lower_nodes(self.nodes[edge.target])
            self.nodes[edge.target].add_upper_nodes(self.nodes[edge.source])

    def __getitem__(self, name: str):
        return self.nodes[name]

    def __iter__(self) -> Iterator[VFGNode]:
        yield from sorted(self.nodes.values(), key=lambda node: node.id)

    def __repr__(self) -> str:
        return f'VFG({self.node_number},{self.edge_number})'

    @property
    def node_number(self) -> int:
        return len(self.nodes)

    @property
    def edge_number(self) -> int:
        return sum(node.upper_node_number + node.lower_node_number for node in self) // 2

    @property
    def size(self) -> tuple[int, int]:
        return self.node_number, self.edge_number

    def get_node_from_id(self, id: int) -> VFGNode:
        """
        Convert node ID to node name.
        """
        for node in self:
            if node.id == id:
                return node
        raise ValueError(f"No node found with ID {id}")

    def search_nodes(self, type: str, function: str, basic_block: str) -> set[VFGNode]:
        matched_nodes: set[VFGNode] = set()
        for node in self:
            if (
                node.type == type and
                node.function == function and
                node.basic_block == basic_block
            ):
                matched_nodes.add(node)
        return matched_nodes

    def write(self, filename: str, name: str, label: str):
        nodes: set[Node] = set()
        edges: set[Edge] = set()

        for node in self:
            nodes.add(Node(node.name, node.compiled_info))
            for upper_node in node.upper_nodes:
                edges.add(Edge(upper_node.name, node.name))
            for lower_node in node.lower_nodes:
                edges.add(Edge(node.name, lower_node.name))
        Graph(nodes, edges, name, label).write(filename)

    @classmethod
    def from_file(cls, filename: str) -> VFG:
        logger.info('Reading VFG from "%s"', filename)
        return cls(Graph.from_file(filename))
