from __future__ import annotations
from typing import Any, TYPE_CHECKING, Callable
import inspect
from dataclasses import Field, MISSING
from magicgui.type_map import get_widget_class
from magicgui.widgets import create_widget
from magicgui.widgets._bases import Widget
from magicgui.widgets._bases.value_widget import UNSET
from .widgets import NotInstalled

if TYPE_CHECKING:
    from magicgui.widgets._protocols import WidgetProtocol
    from magicgui.types import WidgetOptions

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
    
    def __repr__(self):
        return "Magic" + super().__repr__()
    
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
    def param_kind(self) -> inspect._ParameterKind:
        raise NotImplementedError()
    
    @property
    def options(self) -> dict:
        return self.metadata.get("options", {})
    
    @property
    def native(self) -> Widget:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")
    
    @property
    def enabled(self) -> bool:
        return self.options.get("enabled", True)
    
    @property
    def parent(self) -> Widget:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")
    
    @property
    def widget_type(self) -> str:
        if self.default_factory is not MISSING and issubclass(self.default_factory, Widget):
            wcls = self.default_factory
        else:
            wcls = get_widget_class(value=self.value, annotation=self.annotation)
        return wcls.__name__

    @property
    def label(self) -> str:
        return self.options.get("label", True)
    
    @property
    def width(self) -> int:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")
    
    @property
    def min_width(self) -> int:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")

    @property
    def max_width(self) -> int:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")
    
    @property
    def height(self) -> int:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")

    @property
    def min_height(self) -> int:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")

    @property
    def max_height(self) -> int:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")

    @property
    def tooltip(self) -> str | None:
        raise RuntimeError(f"{self!r} has not been converted to a widget yet.")

    @property
    def visible(self) -> bool:
        return self.options.get("visible", True)

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
    options = options.copy()
    metadata = dict(widget_type=widget_type, options=options)
    if isinstance(obj, type):
        f = MagicField(default_factory=obj, metadata=metadata)
    elif obj is MISSING:
        f = MagicField(metadata=metadata)
    else:
        f = MagicField(default=obj, metadata=metadata)
    f.name = name
    return f
