
from __future__ import annotations
from qtpy.QtWidgets import QWidget, QVBoxLayout
from magicgui.widgets._bases import Widget
from magicgui.backends._qtpy.widgets import QBaseWidget

class FreeWidget(Widget):
    """
    A Widget class with any QWidget as a child.
    """    
    def __init__(self, **kwargs):
        super().__init__(widget_type=QBaseWidget, backend_kwargs={"qwidg": QWidget}, **kwargs)
        self.native: QWidget
        self.native.setLayout(QVBoxLayout())
        self.native.setContentsMargins(0, 0, 0, 0)
        
    def set_widget(self, widget: QWidget):
        self.native.layout().addWidget(widget)
        widget.setParent(self.native)
