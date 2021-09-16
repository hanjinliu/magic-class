from __future__ import annotations
from functools import wraps
import inspect
from typing import Iterable, Union
from magicgui.signature import magic_signature, MagicSignature, cast
from magicgui.widgets._bases import Widget

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
        func.__signature__ = magic_signature(func, gui_options=options)
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
        if hasattr(func, "__signature__") and isinstance(func.__signature__, MagicMethodSignature):
            func.__signature__.caller_options.update(caller_options)
        else:
            msig = magic_signature(func, gui_options={})
            func.__signature__ = MagicMethodSignature.from_magicsignature(msig, caller_options=caller_options)
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
    enables = _assert_iterable_of_str(enables)
    disables = _assert_iterable_of_str(disables)
    shows = _assert_iterable_of_str(shows)
    hides = _assert_iterable_of_str(hides)

    def wrapper(func):
        @wraps(func)
        def f(self, *args, **kwargs):
            out = func(self, *args, **kwargs)
            for widget in filter(lambda x: isinstance(x, Widget), self):
                widget: Widget
                if widget.name in enables and not widget.enabled:
                    widget.enabled = True
                elif widget.name in disables and widget.enabled:
                    widget.enabled = False
                elif widget.name in shows and not widget.visible:
                    widget.visible = True
                elif widget.name in hides and widget.visible:
                    widget.visible = False
            return out
        
        if hasattr(f, "__signature__") and isinstance(f.__signature__, MagicMethodSignature):
            f.__signature__.caller_options.update({"enabled": enabled, "visible": visible})
        else:
            msig = magic_signature(func, gui_options={})
            f.__signature__ = MagicMethodSignature.from_magicsignature(
                msig, caller_options={"enabled": enabled, "visible": visible})
        return f
    return wrapper

def upgrade_signature(func, caller_options):
    if hasattr(func, "__signature__") and isinstance(func.__signature__, MagicMethodSignature):
        func.__signature__.caller_options.update(caller_options)
    else:
        msig = magic_signature(func, gui_options={})
        func.__signature__ = MagicMethodSignature.from_magicsignature(
            msig, caller_options=caller_options)
    return func

def _assert_iterable_of_str(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str):
        obj = [obj]
    return obj

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
    def from_signature(cls, sig: MagicSignature, gui_options=None, caller_options=None) -> MagicMethodSignature:
        if type(sig) is cls:
            return cast(MagicSignature, sig)
        elif not isinstance(sig, inspect.Signature):
            raise TypeError("'sig' must be an instance of 'inspect.Signature'")
        sig = MagicSignature.from_signature(sig, gui_options=gui_options)
        return cls.from_magicsignature(sig, caller_options=caller_options)
    
    @classmethod
    def from_magicsignature(cls, sig: MagicSignature, caller_options=None) -> MagicMethodSignature:
        if type(sig) is cls:
            return cast(MagicSignature, sig)
        elif not isinstance(sig, MagicSignature):
            raise TypeError("'sig' must be an instance of MagicSignature")
        return cls(
            list(sig.parameters.values()),
            return_annotation=sig.return_annotation,
            caller_options=caller_options
        )