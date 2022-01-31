
from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout
from qtpy.QtCore import Qt
from magicgui.widgets import Widget
from magicgui.backends._qtpy.widgets import QBaseWidget

if TYPE_CHECKING:
    from ..gui import BaseGui, ContextMenuGui

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
        super().__init__(widget_type=QBaseWidget, backend_kwargs={"qwidg": QWidget}, **kwargs)
        self.native: QWidget
        self.central_widget: QWidget
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
        
    def set_contextmenu(self, contextmenugui: ContextMenuGui):
        from ..gui import ContextMenuGui
        if not isinstance(contextmenugui, ContextMenuGui):
            raise TypeError
        from ..gui.utils import define_context_menu
        self.native.setContextMenuPolicy(Qt.CustomContextMenu)
        self.native.customContextMenuRequested.connect(
            define_context_menu(contextmenugui, self.native)
            )
    
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


def magicwidget(qcls: type[QWidget]):
    from ..utils import iter_members
    for name, attr in iter_members(qcls):
        def _(self: FreeWidget, *args, **kwargs):
            return attr(self.central_widget, *args, **kwargs)
    cls = type(qcls.__name__, (FreeWidget, ), {})
    