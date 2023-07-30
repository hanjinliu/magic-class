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
    @property
    def labels(self) -> bool:
        """Always not labeled."""
        return False


class SingleWidgetBox(Box[_W]):
    @classmethod
    def from_widget(cls, widget: _W):
        out = cls(
            widgets=[widget],
            label=widget.label or widget.name or "",
            name=widget.name,
        )
        out.margins = (0, 0, 0, 0)
        return out

    @property
    def widget(self) -> _W:
        return self[0]

    @property
    def value(self):
        return self.widget.value


class ResizableBox(SingleWidgetBox[_W], ResizableContainer):
    pass


class ScrollableBox(SingleWidgetBox[_W], ScrollableContainer):
    pass


class DraggableBox(SingleWidgetBox[_W], DraggableContainer):
    pass


class CollapsibleBox(SingleWidgetBox[_W], CollapsibleContainer):
    pass


class HCollapsibleBox(SingleWidgetBox[_W], HCollapsibleContainer):
    pass
