from __future__ import annotations
from psygnal.containers import EventedList
from ._base import LayerItem


class LayerList(EventedList[LayerItem]):
    def __init__(self, data=()):
        super().__init__(data=data, hashable=False)
        self.events.removed.connect(self._on_removed)
        self.events.moved.connect(self._on_moved)

    def _on_removed(self, idx: int, value: LayerItem):
        value._visual.parent = None

    def _on_moved(self, obj: tuple[int, int]):
        src, dst = obj
        order_src = self[src]._visual.order
        order_dst = self[dst]._visual.order
        self[src]._visual.order = order_dst
        self[dst]._visual.order = order_src
