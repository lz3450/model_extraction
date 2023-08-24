from __future__ import annotations


class VFGEdge:
    def __init__(self, source: str, target: str, style='solid', color='black'):
        self._source = source
        self._target = target
        self._style = style
        self._color = color

    @property
    def source(self) -> str:
        return self._source

    @property
    def target(self) -> str:
        return self._target

    @property
    def style(self) -> str:
        return self._style

    @property
    def color(self) -> str:
        return self._color

    def reverse(self):
        self._source, self._target = self._target, self._source

    def __repr__(self) -> str:
        return f'Edge({self._source} → {self._target})'
