from __future__ import annotations


class VFGEdge:
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

    # def __eq__(self, other) -> bool:
    #     return self._source == other.source and self._target == other._target if isinstance(other, VFGEdge) else False
