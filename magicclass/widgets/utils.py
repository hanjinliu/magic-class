
from __future__ import annotations
from qtpy.QtWidgets import QWidget, QVBoxLayout
from magicgui.widgets._bases import Widget
from magicgui.backends._qtpy.widgets import QBaseWidget

class FreeWidget(Widget):
    """
    Non-editable container. 
    This class is useful to add QWidget into Container. If a QWidget is added via 
    Container.layout(), it will be invisible from Container. We can solve this
    problem by "wrapping" a QWidget with a Container.
    """    
    def __init__(self, **kwargs):
        super().__init__(widget_type=QBaseWidget, backend_kwargs={"qwidg": QWidget}, **kwargs)
        self.native: QWidget
        self.native.setLayout(QVBoxLayout())
        self.native.setContentsMargins(0, 0, 0, 0)
        
    def set_widget(self, widget: QWidget):
        self.native.layout().addWidget(widget)
        widget.setParent(self.native)
