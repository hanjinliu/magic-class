from __future__ import annotations
from functools import wraps
import inspect
from typing import Callable, Iterable, Iterator, Union, TYPE_CHECKING
from magicgui.signature import MagicSignature
from magicgui.widgets._bases import ButtonWidget

if TYPE_CHECKING:
    from .class_gui import ClassGui

Color = Union[str, Iterable[float]]
nStrings = Union[str, Iterable[str]]

def set_options(**options):
    """
    Set MagicSignature to functions. By decorating a function like below:
    
    >>> @set_options(x={"value": -1})
    >>> def func(x):
    >>>     ...
    
    then magicgui knows what widget it should be converted to. 
    """    
    def wrapper(func):
        upgrade_signature(func, gui_options=options)
        return func
    return wrapper

def button_design(width:int=None, height:int=None, min_width:int=None, min_height:int=None,
                  max_width:int=None, max_height:int=None, text:str=None, 
                  icon_path:str=None, icon_size:tuple[int,int]=None,
                  font_size:int=None, font_family:int=None, font_color:Color=None,
                  background_color:Color=None):
    """
    Change button design by calling setter when the button is created.

    Parameters
    ----------
    width : int, optional
        Button width. Call ``button.width = width``.
    height : int, optional
        Button height. Call ``button.height = height``.
    min_width : int, optional
        Button minimum width. Call ``button.min_width = min_width``.
    min_height : int, optional
        Button minimum height. Call ``button.min_height = min_height``.
    max_width : int, optional
        Button maximum width. Call ``button.max_width = max_width``.
    max_height : int, optional
        Button maximum height. Call ``button.max_height = max_height``.
    text : str, optional
        Button text. Call ``button.text = text``.
    icon_path : str, optional
        Path to icon file. ``min_width`` and ``min_height`` will be automatically set to the icon size
        if not given.
    icon_size : tuple of two int, optional
        Icon size.
    font_size : int, optional
        Font size of the text.
    """    
    if icon_size is not None:
        if min_width is None:
            min_width = icon_size[0]
        if min_height is None:
            min_height = icon_size[1]
    caller_options = dict(width=width, height=height, min_width=min_width, min_height=min_height,
                          max_width=max_width, max_height=max_height, text=text, icon_path=icon_path,
                          icon_size=icon_size, font_size=font_size, font_family=font_family,
                          font_color=font_color, background_color=background_color)
    def wrapper(func):
        upgrade_signature(func, caller_options=caller_options)
        return func
    return wrapper

def click(enables:nStrings=None, disables:nStrings=None, enabled:bool=True,
          shows:nStrings=None, hides:nStrings=None, visible:bool=True):
    """
    Set options of push buttons related to button clickability.
    
    Parameters
    ----------
    enables : str or iterable of str, optional
        Enables other button(s) in this list when clicked.
    disables : str or iterable of str, optional
        Disables other button(s) in this list when clicked.
    enabled : bool, default is True
        The initial clickability state of the button.
    shows : str or iterable of str, optional
        Make other button(s) in this list visible when clicked.
    hides : str or iterable of str, optional
        Make other button(s) in this list invisible when clicked.
    visible: bool, default is True
        The initial visibility of the button.
    """
    enables = _assert_iterable(enables)
    disables = _assert_iterable(disables)
    shows = _assert_iterable(shows)
    hides = _assert_iterable(hides)
    
    def wrapper(func):   
        @wraps(func)
        def f(self, *args, **kwargs):
            out = func(self, *args, **kwargs)
            for button in _iter_button_widgets(self, enables):
                button.enabled = True
            for button in _iter_button_widgets(self, disables):
                button.enabled = False
            for button in _iter_button_widgets(self, shows):
                button.visible = True
            for button in _iter_button_widgets(self, hides):
                button.visible = False
            
            return out
        
        caller_options = {"enabled": enabled, "visible": visible}
        upgrade_signature(f, caller_options=caller_options)
        return f
    return wrapper

def upgrade_signature(func, gui_options:dict=None, caller_options:dict=None):
    gui_options = gui_options or {}
    caller_options = caller_options or {}
    
    sig = _get_signature(func)
    
    new_gui_options = MagicMethodSignature.get_gui_options(sig).copy()
    new_gui_options.update(gui_options)
    
    new_caller_options = getattr(sig, "caller_options", {}).copy()
    new_caller_options.update(caller_options)

    func.__signature__ = MagicMethodSignature.from_signature(
            sig, gui_options=new_gui_options, caller_options=new_caller_options)

    return func

def _get_signature(func):
    if hasattr(func, "__signature__"):
        sig = func.__signature__
    else:
        sig = inspect.signature(func)
    return sig

def _assert_iterable(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str) or callable(obj):
        obj = [obj]
    return obj

def _iter_button_widgets(self:ClassGui, descriptors:Iterable[list[str]] | Iterable[Callable]
                         ) -> Iterator[ButtonWidget]:
    for f in descriptors:
        if callable(f):
            # A.B.func -> B.func, if self is an object of A.
            f = f.__qualname__.split(self.__class__.__name__)[1][1:]
            
        if isinstance(f, str):
            *clsnames, funcname = f.split(".")
            # search for parent class that match the description.
            ins = self
            for a in clsnames:
                if a != "":
                    ins = getattr(ins, a)
                else:
                    ins = ins.__magicclass_parent__
            
            button = ins[funcname]
            if not isinstance(button, ButtonWidget):
                s = ".".join(descriptors)
                raise TypeError(f"{button} is not a button. This exception happened due to {s}.")
        else:
            raise TypeError(f"Unexpected type in click decorator: {type(f)}")
        yield button


class MagicMethodSignature(MagicSignature):
    """
    This class also retains parameter options for PushButton itself, aside from the FunctionGui options
    that will be needed when the button is pushed.
    """    
    def __init__(
        self,
        parameters = None,
        *,
        return_annotation=inspect.Signature.empty,
        gui_options: dict[str, dict] = None,
        caller_options: dict[str] = None
    ):
        super().__init__(parameters=parameters, return_annotation=return_annotation, gui_options=gui_options)
        self.caller_options = caller_options
    
    @classmethod
    def from_signature(cls, sig: inspect.Signature, gui_options=None, caller_options=None) -> MagicMethodSignature:
        if not isinstance(sig, inspect.Signature):
            raise TypeError("'sig' must be an instance of 'inspect.Signature'")
        # prepare parameters again
        parameters = {k: inspect.Parameter(param.name,
                                           param.kind,
                                           default=param.default,
                                           annotation=param.annotation) 
                      for k, param in sig.parameters.items()}
        
        return cls(
            list(parameters.values()),
            return_annotation=sig.return_annotation,
            gui_options=gui_options,
            caller_options=caller_options
            )
    
    @classmethod
    def get_gui_options(cls, self:inspect.Signature|MagicSignature):
        if type(self) is inspect.Signature:
            return {}
        else:
            return {k: v.options for k, v in self.parameters.items()}