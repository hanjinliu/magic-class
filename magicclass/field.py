from __future__ import annotations
import sys
from typing import Any, TYPE_CHECKING
from magicgui.widgets import  create_widget
from magicgui.widgets._bases import Widget
from magicgui.widgets._protocols import WidgetProtocol
from dataclasses import Field, MISSING

if TYPE_CHECKING:
    from magicgui.types import WidgetOptions

class MagicField(Field):
    """
    Field class for magicgui construction.
    """    
    def __init__(self, default=MISSING, default_factory=MISSING, metadata:dict={}):
        metadata = metadata.copy()
        if default is MISSING:
            default = metadata.pop("value", MISSING)
        super().__init__(default=default, default_factory=default_factory, init=True, repr=True, 
                         hash=False, compare=False, metadata=metadata)
        self.lineno = -1
    
    def ready(self) -> bool:
        return not self.not_ready()
    
    def not_ready(self) -> bool:
        return self.default is MISSING and self.default_factory is MISSING

    def to_widget(self) -> Widget:
        """
        Create a widget from the field.

        Returns
        -------
        Widget
            Widget object that is ready to be inserted into Container.

        Raises
        ------
        ValueError
            If there is not enough information to build a widget.
        """        
        value = None if self.default is MISSING else self.default
        annotation = None if self.default_factory is MISSING else self.default_factory
        
        if self.default_factory is not MISSING and issubclass(self.default_factory, Widget):
            widget = self.default_factory(**self.metadata.get("options", {}))
        else:
            widget = create_widget(value=value, 
                                   annotation=annotation,
                                   **self.metadata
                                   )
        widget.name = self.name
        return widget

def field(obj:Any=MISSING, name:str="", widget_type:str|type[WidgetProtocol]|None = None, 
          options:WidgetOptions={}) -> MagicField:
    """
    Make a MagicField object.
    
    >>> i = field(1)
    >>> i:int = field()
    >>> i:int = field(widget_type="Slider")
    >>> i = 

    Parameters
    ----------
    obj : Any, default is MISSING
        Reference to determine what type of widget will be created. If Widget subclass is given, 
        it will be used as is. If other type of class is given, it will used as type annotation.
        If an object (not type) is given, it will be assumed to be the default value.
    name : str, default is ""
        Name of the widget.
    widget_type : str, optional
        Widget type. This argument will be sent to ``create_widget`` function.
    options : WidgetOptions, optional
        Widget options. This parameter will always be used in ``widget(**options)`` form.

    Returns
    -------
    MagicField
    """    
    options = options.copy()
    metadata = dict(widget_type=widget_type, options=options)
    if isinstance(obj, type):
        f = MagicField(default_factory=obj, metadata=metadata)
    elif obj is MISSING:
        f = MagicField(metadata=metadata)
    else:
        f = MagicField(default=obj, metadata=metadata)
    f.lineno = current_location(2)
    f.name = name
    return f

def current_location(depth:int=0):
    """
    Get the current location in the source code.
    """    
    frame = sys._getframe(depth)
    return frame.f_lineno