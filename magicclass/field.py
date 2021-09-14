import sys
from magicgui.widgets import  create_widget
from magicgui.widgets._bases import Widget
from dataclasses import Field, MISSING

class MagicField(Field):
    def __init__(self, default_factory, metadata):
        super().__init__(default=MISSING, default_factory=default_factory, init=True, repr=True, 
                         hash=False, compare=False, metadata=metadata)
        self.lineno = -1

    def to_widget(self) -> Widget:
        if issubclass(self.default_factory, Widget):
            widget = self.default_factory(**self.metadata)
        else:
            widget = create_widget(annotation=self.default_factory, **self.metadata)
        widget.name = self.name
        return widget

def field(cls:type=None, name:str="", **options) -> MagicField:
    f = MagicField(default_factory=cls, metadata=options)
    f.lineno = current_location(2)
    f.name = name
    return f

def current_location(depth:int=0):
    """
    Get the current location in the source code.
    """    
    frame = sys._getframe(depth)
    return frame.f_lineno