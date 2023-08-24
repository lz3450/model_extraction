from typing import Iterator, Iterable
import re
import logging

from .vfg_edge import VFGEdge
from .log import config_logger

logger = logging.getLogger(__name__)
config_logger(logger)


class VFGNode:
    def __init__(self, name: str, label: str = '', shape: str = 'record', color: str = 'black', penwidth: int = 2):
        self._name = name
        self._shape = shape
        self._color = color
        self._penwidth = penwidth
        self._info = re.split(r',\\n\s*', label)
        self._edges: set[VFGEdge] = set()
        self._type, self._id = self._info[0].split(" ID: ")
        if self._info[2] != '(none)':
            self._ir = self._info[2]
        else:
            self._ir = ''
            if self.type not in {'NullPtrVFGNode', 'FormalRetVFGNode'}:
                logger.warning('%s (%d) does not contains IR code', self.type, self.id)
        match = re.search(r'Function\[(\S+)\]', self._ir)
        if match:
            self._function = match.group(1)
        else:
            self._function = ''
        match = re.search(r'BasicBlock\[(\S+)\]', self._ir)
        if match:
            self._basic_block = match.group(1)
        else:
            self._basic_block = ''
        if self.type == 'ActualRetVFGNode':
            self._params = ()
        self._label = self._label_format()

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
    def shape(self) -> str:
        return self._shape

    @property
    def color(self) -> str:
        return self._color
    
    @property
    def penwidth(self) -> int:
        return self._penwidth

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
        return self._function

    @property
    def basic_block(self) -> str:
        return self._basic_block

    @property
    def params(self) -> tuple:
        if self.type != 'ActualRetVFGNode':
            raise ValueError(f'"{self.type}" does not have param labels.')
        return self._params

    @params.setter
    def params(self, values: Iterable):
        self._params = tuple(values)

    @property
    def param_number(self) -> int:
        return len(self.params)

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

    def _label_format(self) -> str:
        """Transform the label of the node."""
        if not self.ir:
            return self.ir
        match self.type:
            case 'AddrVFGNode':
                pattern = re.compile(r'(\S+) = .+')
                match = pattern.match(self.ir)
                if match:
                    return match.group(1)
            case 'LoadVFGNode':
                pattern = re.compile(r'(%\S+) = load .+([%@]\S+),')
                match = pattern.match(self.ir)
                if match:
                    return f'{match.group(2)} → {match.group(1)}'
            case 'StoreVFGNode':
                pattern = re.compile(r'store \S+ (\S+), \S+ (%\S+),')
                match = pattern.match(self.ir)
                if match:
                    return f'{match.group(1)} → {match.group(2)}'
            case 'CopyVFGNode':
                pattern = re.compile(
                    r'(%\S+) = (sitofp|fpext|bitcast|fptrunc) .+ (%\S+) to .+,')
                match = pattern.match(self.ir)
                if match:
                    return f'{match.group(3)} → {match.group(1)}'
            case 'FormalParmVFGNode':
                pattern = re.compile(r'\S+ (%\S+)')
                match = pattern.match(self.ir)
                if match:
                    return match.group(1)
            case 'ActualParmVFGNode':
                if ' = ' in self.ir:
                    pattern = re.compile(r'(%\S+) = .+')
                else:
                    pattern = re.compile(r'\S+ (%\S+)')
                match = pattern.match(self.ir)
                if match:
                    return match.group(1)
            case 'ActualRetVFGNode':
                pattern = re.compile(r'(%\S+) = (call|invoke) .+ (@\S+)\((.+)\)')
                match = pattern.match(self.ir)
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
                    self.params = param_labels
                    return f"{retval} = {func_name}({', '.join(param_labels)})"
            case 'BinaryOPVFGNode':
                pattern = re.compile(r'(%\S+) = (fmul|fadd) .+ (%\S+), (%\S+)')
                match = pattern.match(self.ir)
                if match:
                    return f'{match.group(1)} = {match.group(2)}({match.group(3)}, {match.group(4)})'
            case 'GepVFGNode':
                pattern = re.compile(r'(%\S+) = getelementptr inbounds (%\S+), (%\S+) (%\S+), (\S+) (\d+), (\S+) (\d+)')
                match = pattern.match(self.ir)
                if match:
                    element = match.group(1)
                    ptrvar = match.group(4)
                    return f'{ptrvar}.{element}'
            case 'IntraPHIVFGNode':
                assert self.function is not None
                return self.function
        return self.ir

    def add_edge(self, edge: VFGEdge) -> None:
        self._edges.add(edge)

    def remove_edge(self, edge: VFGEdge) -> None:
        self._edges.remove(edge)

    def has_edge(self, node_name: str, direction: str) -> bool:
        if direction not in ('in', 'out'):
            raise ValueError("`direction` should be \"in\" or \"out\".")

        attribute = 'source' if direction == 'in' else 'target'

        return any(getattr(edge, attribute) == node_name for edge in self._edges)

    def __iter__(self):
        yield from self._edges

    def __repr__(self) -> str:
        return f'{self._type}({self._id}, "{self._name}")'
