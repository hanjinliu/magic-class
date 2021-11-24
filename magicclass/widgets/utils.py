
from __future__ import annotations
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout
from qtpy.QtWidgets import QWidget, QVBoxLayout
from magicgui.widgets import Widget
from magicgui.backends._qtpy.widgets import QBaseWidget

class FreeWidget(Widget):
    """
    A Widget class with any QWidget as a child.
    """    
    def __init__(self, layout="vertical", **kwargs):
        super().__init__(widget_type=QBaseWidget, backend_kwargs={"qwidg": QWidget}, **kwargs)
        self.native: QWidget
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
