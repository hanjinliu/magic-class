from __future__ import annotations
from functools import wraps
import inspect
from typing import Iterable
from magicgui.signature import magic_signature, MagicSignature, cast
from magicgui.widgets import PushButton

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

def button_design(width=None, height=None, min_width=None, min_height=None,
                  max_width=None, max_height=None, text=None):
    
    caller_options = dict(width=width, height=height, min_width=min_width, min_height=min_height,
                          max_width=max_width, max_height=max_height, text=text)
    def wrapper(func):
        if hasattr(func, "__signature__") and isinstance(func.__signature__, MagicMethodSignature):
            func.__signature__.caller_options.update(caller_options)
        else:
            msig = magic_signature(func, gui_options={})
            func.__signature__ = MagicMethodSignature.from_magicsignature(msig, caller_options={caller_options})
        return func
    return wrapper

def click(enables:str|Iterable[str]=None, disables:str|Iterable[str]=None, 
          switches:str|Iterable[str]=None, enabled:bool=True):
    """
    Set options of push buttons related to button clickability.
    
    Parameters
    ----------
    enables : str or iterable of str, optional
        Enables other button(s) in this list when clicked.
    disables : str or iterable of str, optional
        Disables other button(s) in this list when clicked.
    switches : str or iterable of str, optional
        Switches the states of other button(s) in this list when clicked.
    enabled : bool, default is True
        The initial clickability state of the button.
    """
    enables = _assert_iterable_of_str(enables)
    disables = _assert_iterable_of_str(disables)
    switches = _assert_iterable_of_str(switches)

    def wrapper(func):
        @wraps(func)
        def f(self, *args, **kwargs):
            out = func(self, *args, **kwargs)
            for button in filter(lambda x: isinstance(x, PushButton), self):
                button: PushButton
                if button.name in enables and not button.enabled:
                    button.enabled = True
                elif button.name in disables and button.enabled:
                    button.enabled = False
                elif button.name in switches:
                    button.enabled = not button.enabled
            return out
        
        if hasattr(func, "__signature__") and isinstance(func.__signature__, MagicMethodSignature):
            func.__signature__.caller_options.update({"enabled": enabled})
        else:
            msig = magic_signature(func, gui_options={})
            f.__signature__ = MagicMethodSignature.from_magicsignature(msig, caller_options={"enabled": enabled})
        return f
    return wrapper


def _assert_iterable_of_str(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str):
        obj = [obj]
    return obj

class MagicMethodSignature(MagicSignature):
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