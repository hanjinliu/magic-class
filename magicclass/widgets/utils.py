
from __future__ import annotations
from functools import wraps
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout
from magicgui.widgets import Widget
from magicgui.backends._qtpy.widgets import QBaseWidget

class FreeWidget(Widget):
    """
    A Widget class with any QWidget as a child.
    """    
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
            ValueError(layout)
        self.native.setContentsMargins(0, 0, 0, 0)
        
    def set_widget(self, widget: QWidget, *args):
        self.native.layout().addWidget(widget, *args)
        widget.setParent(self.native)
        self.central_widget = widget

def magicwidget(qcls: type[QWidget]):
    @wraps(qcls.__init__)
    def __init__(self: FreeWidget, *args, **kwargs):
        FreeWidget.__init__(self)
        self._qwidget = qcls.__init__(*args, **kwargs)
        self.set_widget(self._qwidget)
    
    new_class = type(qcls.__name__, (FreeWidget,), {})
    new_class.__init__ = __init__
    return new_class
