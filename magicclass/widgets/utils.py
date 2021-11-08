
from __future__ import annotations
from qtpy.QtWidgets import QWidget
from magicgui.widgets import Container

class FrozenContainer(Container):
    """
    Non-editable container. 
    This class is useful to add QWidget into Container. If a QWidget is added via 
    Container.layout(), it will be invisible from Container. We can solve this
    problem by "wrapping" a QWidget with a Container.
    """    
    def insert(self, key, value):
        raise AttributeError(f"Cannot insert widget to {self.__class__.__name__}")
    
    def set_widget(self, widget: QWidget):
        self.native.layout().addWidget(widget)
        self.margins = (0, 0, 0, 0)
        widget.setParent(self.native)