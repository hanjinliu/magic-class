
from __future__ import annotations
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout
from magicgui.widgets import Widget
from magicgui.backends._qtpy.widgets import QBaseWidget


class _NotInitialized:
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


    def set_widget(self, widget: QWidget, *args):
        """Set the central widget to the widget."""
        self.native.layout().addWidget(widget, *args)
        widget.setParent(self.native)
        self.central_widget = widget

def magicwidget(qcls: type[QWidget]):
    from ..utils import iter_members
    for name, attr in iter_members(qcls):
        def _(self: FreeWidget, *args, **kwargs):
            return attr(self.central_widget, *args, **kwargs)
    cls = type(qcls.__name__, (FreeWidget, ), {})
    