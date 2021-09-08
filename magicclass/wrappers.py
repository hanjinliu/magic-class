from __future__ import annotations
from functools import wraps
from typing import Iterable
from magicgui.signature import magic_signature
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
    enables = _assert_iterable_of_funcname(enables)
    disables = _assert_iterable_of_funcname(disables)
    switches = _assert_iterable_of_funcname(switches)

    def wrapper(func):
        @wraps(func)
        def f(self, *args, **kwargs):
            out = func(self, *args, **kwargs)
            for button in filter(lambda x: isinstance(x, PushButton), self):
                button:PushButton
                if button.text in enables and not button.enabled:
                    button.enabled = True
                elif button.text in disables and button.enabled:
                    button.enabled = False
                elif button.text in switches:
                    button.enabled = not button.enabled
            return out
        
        # This is not an elegant solution, but is there a better way?
        f.__signature__ = magic_signature(func, gui_options={})
        f.__signature__.enabled = enabled
        return f
    return wrapper

def _assert_iterable_of_funcname(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str):
        obj = [obj]
    obj = [s.replace("_", " ") for s in obj]
    return obj
    