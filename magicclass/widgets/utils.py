from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout
from magicgui.widgets import Widget
from magicgui.widgets._concrete import merge_super_sigs as _merge_super_sigs
from magicgui.backends._qtpy.widgets import QBaseWidget

if TYPE_CHECKING:
    from magicclass._gui import BaseGui, ContextMenuGui


class _NotInitialized:
    """This class helps better error handling."""

    def __init__(self, msg: str):
        self.msg = msg

    def __getattr__(self, key: str):
        raise RuntimeError(self.msg)


class FreeWidget(Widget):
    """A Widget class with any QWidget as a child."""

    _widget = _NotInitialized(
        "Widget is not correctly initialized. Must call `super().__init__` before using "
        "the widget."
    )

    def __init__(self, layout="vertical", **kwargs):
        super().__init__(
            widget_type=QBaseWidget, backend_kwargs={"qwidg": QWidget}, **kwargs
        )
        self.native: QWidget
        self.central_widget: QWidget | None = None
        if layout == "vertical":
            self.native.setLayout(QVBoxLayout())
        elif layout == "horizontal":
            self.native.setLayout(QHBoxLayout())
        elif layout == "grid":
            self.native.setLayout(QGridLayout())
        else:
            raise ValueError(layout)
        self.native.setContentsMargins(0, 0, 0, 0)
        self._magicclass_parent_ref = None

    def set_widget(self, widget: QWidget, *args):
        """Set the central widget to the widget."""
        self.native.layout().addWidget(widget, *args)
        widget.setParent(self.native)
        self.central_widget = widget

    def remove_widget(self, widget: QWidget):
        """Set the central widget from the widget."""
        self.native.layout().removeWidget(widget)
        widget.setParent(None)
        self.central_widget = None

    def set_contextmenu(self, contextmenugui: ContextMenuGui):
        contextmenugui._set_magic_context_menu(self)

    @property
    def __magicclass_parent__(self) -> BaseGui | None:
        """Return parent magic class if exists."""
        if self._magicclass_parent_ref is None:
            return None
        parent = self._magicclass_parent_ref()
        return parent

    @__magicclass_parent__.setter
    def __magicclass_parent__(self, parent) -> None:
        if parent is None:
            return
        self._magicclass_parent_ref = weakref.ref(parent)


def merge_super_sigs(cls):
    cls = _merge_super_sigs(cls)
    cls.__module__ = "magicclass.widgets"
    return cls
