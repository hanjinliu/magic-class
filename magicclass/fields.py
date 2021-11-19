from __future__ import annotations
from typing import Any, TYPE_CHECKING, Callable, TypeVar
from dataclasses import Field, MISSING
from magicgui.type_map import get_widget_class
from magicgui.widgets import create_widget
from magicgui.widgets._bases import Widget
from magicgui.widgets._bases.value_widget import UNSET
from .widgets import NotInstalled

if TYPE_CHECKING:
    from magicgui.widgets._protocols import WidgetProtocol
    from magicgui.types import WidgetOptions
    
X = TypeVar("X")

class MagicField(Field):
    """
    Field class for magicgui construction. This object is compatible with dataclass.
    """    
    def __init__(self, default=MISSING, default_factory=MISSING, metadata: dict = {}):
        metadata = metadata.copy()
        if default is MISSING:
            default = metadata.pop("value", MISSING)
        super().__init__(default=default, default_factory=default_factory, init=True, repr=True, 
                         hash=False, compare=False, metadata=metadata)
        self.callbacks: list[Callable] = []
        self.guis: dict[int, X] = {}
    
    def __repr__(self):
        return self.__class__.__name__.rstrip("Field") + super().__repr__()
    
    def get_widget(self, obj: X) -> Widget:
        obj_id = id(obj)
        if obj_id in self.guis.keys():
            widget = self.guis[obj_id]
        else:
            widget = self.to_widget()
            self.guis[obj_id] = widget
                
        return widget
    
    def __get__(self, obj: X, objtype=None):
        if obj is None:
            return self
        return self.get_widget(obj)
    
    def __set__(self, obj: X, value) -> None:
        raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        
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
        if self.default_factory is not MISSING and issubclass(self.default_factory, Widget):
            widget = self.default_factory(**self.options)
        else:
            if isinstance(self.value, NotInstalled):
                self.value() # raise ModuleNotFoundError here
                
            widget = create_widget(value=self.value, 
                                   annotation=self.annotation,
                                   **self.metadata
                                   )
        widget.name = self.name
        return widget
        
    def connect(self, func: Callable) -> Callable:
        """
        Set callback function to "ready to connect" state.
        """        
        if not callable(func):
            raise TypeError("Cannot connect non-callable object")
        self.callbacks.append(func)
        return func

    @property
    def value(self) -> Any:
        return UNSET if self.default is MISSING else self.default
    
    @property
    def annotation(self):
        return None if self.default_factory is MISSING else self.default_factory
    
    @property
    def options(self) -> dict:
        return self.metadata.get("options", {})
    
    @property
    def widget_type(self) -> str:
        if self.default_factory is not MISSING and issubclass(self.default_factory, Widget):
            wcls = self.default_factory
        else:
            wcls = get_widget_class(value=self.value, annotation=self.annotation)
        return wcls.__name__


class MagicValueField(MagicField):
    def get_widget(self, obj: X):
        widget = super().get_widget(obj)
        if not hasattr(widget, "value"):
            raise TypeError("Widget is not a value widget or a widget with value: "
                           f"{type(widget)}")
        
        return widget
    
    def __get__(self, obj: X, objtype=None):
        if obj is None:
            return self
        return self.get_widget(obj).value
    
    def __set__(self, obj: X, value) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        self.get_widget(obj).value = value

def field(obj: Any = MISSING,
          *, 
          name: str = "", 
          widget_type: str | type[WidgetProtocol] | None = None, 
          options: WidgetOptions = {}
          ) -> MagicField:
    """
    Make a MagicField object.
    
    >>> i = field(1)
    >>> i = field(widget_type="Slider")

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
    return _get_field(obj, name, widget_type, options, MagicField)

def vfield(obj: Any = MISSING,
           *, 
           name: str = "", 
           widget_type: str | type[WidgetProtocol] | None = None, 
           options: WidgetOptions = {}
           ) -> MagicValueField:
    """
    Make a MagicValueField object.
    
    >>> i = vfield(1)
    >>> i = vfield(widget_type="Slider")
    
    Unlike MagicField, value itself can be accessed.
    
    >>> ui.i      # int is returned
    >>> ui.i = 3  # set value to the widget.

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
    MagicValueField
    """    
    return _get_field(obj, name, widget_type, options, MagicValueField)

def _get_field(obj, 
               name: str, 
               widget_type: str | type[WidgetProtocol] | None, 
               options: WidgetOptions,
               field_class: type[MagicField]
               ):
    options = options.copy()
    metadata = dict(widget_type=widget_type, options=options)
    if isinstance(obj, type):
        f = field_class(default_factory=obj, metadata=metadata)
    elif obj is MISSING:
        f = field_class(metadata=metadata)
    else:
        f = field_class(default=obj, metadata=metadata)
    f.name = name
    return f

    
