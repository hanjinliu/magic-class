from __future__ import annotations
from functools import wraps
from typing import Iterable
from magicgui.signature import magic_signature
from magicgui.widgets import PushButton

def set_options(enabled=True, **options):
    """
    Set MagicSignature to functions. By decorating a function like below:
    
    >>> @set_options(x={"value": -1})
    >>> def func(x):
    >>>     ...
    
    then magicgui knows what widget it should be converted to. 
    Set ``enabled=False`` to disable push button when GUI starts.
    """    
    def wrapper(func):
        func.__signature__ = magic_signature(func, gui_options=options)
        
        # This is not an elegant solution, but is there a better way?
        func.__signature__.enabled = enabled
        return func
    return wrapper

def connect(enables:str|Iterable[str]=None, disables:str|Iterable[str]=None, 
            switches:str|Iterable[str]=None):
    """
    Connect button click event to change the states of other buttons.

    Parameters
    ----------
    enables : str or iterable of str, optional
        Enables other button(s) in this list when clicked.
    disables : str or iterable of str, optional
        Disables other button(s) in this list when clicked.
    switches : str or iterable of str, optional
        Switches the states of other button(s) in this list when clicked.
    """
    enables = _assert_iterable_of_funcname(enables)
    disables = _assert_iterable_of_funcname(disables)
    switches = _assert_iterable_of_funcname(switches)

    def wrapper(func):
        @wraps(func)
        def disabled(self, *args, **kwargs):
            out = func(self, *args, **kwargs)
            for button in filter(lambda x: isinstance(x, PushButton), self):
                if button.text in enables and not button.enabled:
                    button.enabled = True
                elif button.text in disables and button.enabled:
                    button.enabled = False
                elif button.text in switches:
                    button.enabled = not button.enabled
            return out
        return disabled
    return wrapper

def _assert_iterable_of_funcname(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str):
        obj = [obj]
    obj = [s.replace(" ", "_") for s in obj]
    return obj
    