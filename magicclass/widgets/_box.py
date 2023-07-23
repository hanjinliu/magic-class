from __future__ import annotations

from typing import TypeVar
from magicgui.widgets import Widget
from magicgui.widgets.bases import ContainerWidget
from magicclass.widgets.containers import (
    DraggableContainer,
    ResizableContainer,
    ScrollableContainer,
    CollapsibleContainer,
    HCollapsibleContainer,
)

_W = TypeVar("_W", bound=Widget)


class Box(ContainerWidget[_W]):
    @classmethod
    def from_widget(cls, widget: _W):
        out = cls(
            widgets=[widget],
            label=widget.label or widget.name or "",
            name=widget.name,
        )
        return out

    @property
    def widget(self) -> _W:
        return self[0]

    @property
    def labels(self) -> bool:
        return False


class ResizableBox(Box, ResizableContainer):
    pass


class ScrollableBox(Box, ScrollableContainer):
    pass


class DraggableBox(Box, DraggableContainer):
    pass


class CollapsibleBox(Box, CollapsibleContainer):
    pass
