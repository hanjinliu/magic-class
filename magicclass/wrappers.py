from __future__ import annotations
from functools import wraps
from typing import Callable, Iterable, Iterator, Union, TYPE_CHECKING
from magicgui.widgets._bases import ButtonWidget
from .signature import upgrade_signature

if TYPE_CHECKING:
    from ._base import BaseGui
    from magicclass.menu_gui import Action

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

def set_design(width: int = None, height: int = None, min_width: int = None, min_height: int = None,
               max_width: int = None, max_height: int = None, text: str = None, 
               icon_path: str = None, icon_size: tuple [ int,int]=None,
               font_size: int = None, font_family: int = None, font_color: Color = None,
               background_color: Color = None):
    """
    Change button/action design by calling setter when the widget is created.

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
            
    caller_options = locals()
    def wrapper(func):
        upgrade_signature(func, caller_options=caller_options)
        return func
    return wrapper

def click(enables: nStrings = None, disables: nStrings = None, enabled: bool = True,
          shows: nStrings = None, hides: nStrings = None, visible: bool = True):
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
            for button in _iter_widgets(self, enables):
                button.enabled = True
            for button in _iter_widgets(self, disables):
                button.enabled = False
            for button in _iter_widgets(self, shows):
                button.visible = True
            for button in _iter_widgets(self, hides):
                button.visible = False
            
            return out
        
        caller_options = {"enabled": enabled, "visible": visible}
        upgrade_signature(f, caller_options=caller_options)
        return f
    return wrapper

def do_not_record(method: Callable):
    """
    Wrapped method will not be recorded in macro.
    """    
    upgrade_signature(method, additional_options={"record": False})
    return method
    

def _assert_iterable(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str) or callable(obj):
        obj = [obj]
    return obj

def _iter_widgets(self: BaseGui, 
                  descriptors: Iterable[list[str]] | Iterable[Callable]
                  ) -> Iterator[ButtonWidget|Action]:
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
        else:
            raise TypeError(f"Unexpected type in click decorator: {type(f)}")
        yield button

