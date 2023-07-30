from __future__ import annotations

from typing import TypeVar
import weakref
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
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._magicclass_parent_ref = None

    @property
    def __magicclass_parent__(self):
        if self._magicclass_parent_ref is None:
            return None
        return self._magicclass_parent_ref()

    @__magicclass_parent__.setter
    def __magicclass_parent__(self, value):
        if value is None:
            self._magicclass_parent_ref = None
        self._magicclass_parent_ref = weakref.ref(value)

    @property
    def labels(self) -> bool:
        """Always not labeled."""
        return False


class SingleWidgetBox(Box):
    @classmethod
    def from_widget(cls, widget: _W):
        out = cls(
            widgets=[widget],
            label=widget.label or widget.name or "",
            name=widget.name,
        )
        if hasattr(type(widget), "__magicclass_parent__"):
            widget.__magicclass_parent__ = out
        return out

    @property
    def widget(self) -> _W:
        return self[0]

    @property
    def value(self):
        return self.widget.value


class ResizableBox(SingleWidgetBox, ResizableContainer):
    pass


class ScrollableBox(SingleWidgetBox, ScrollableContainer):
    pass


class DraggableBox(SingleWidgetBox, DraggableContainer):
    pass


class CollapsibleBox(SingleWidgetBox, CollapsibleContainer):
    pass


class HCollapsibleBox(SingleWidgetBox, HCollapsibleContainer):
    pass
