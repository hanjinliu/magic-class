from __future__ import annotations
import inspect
from .basegui import BaseGui
from .utils import check_collision, get_app

def magicclass(cls:type|None=None, layout:str="vertical", close_on_run:bool=True):
    """
    Decorator that can convert a Python class into a widget with push buttons.
    
    >>> @magicclass
    >>> class C:
    >>>     ...
    >>> c = C(a=0)
    >>> c.show()
            
    Parameters
    ----------
    cls : type, optional
        Class to be decorated.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    def wrapper(cls):
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        
        check_collision(cls, BaseGui)
        doc = cls.__doc__
        sig = inspect.signature(cls)
        oldclass = type(cls.__name__ + "_Base", (cls,), {})
        newclass = type(cls.__name__, (BaseGui, oldclass), {})
        newclass.__signature__ = sig
        newclass.__doc__ = doc
        
        def __init__(self, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!
            super(oldclass, self).__init__(*args, **kwargs)
            BaseGui.__init__(self, layout=layout, close_on_run=close_on_run, name=oldclass.__name__)
            self._convert_methods_into_widgets()
            if hasattr(self, "__post_init__"):
                self.__post_init__()

        setattr(newclass, "__init__", __init__)
        return newclass
    
    return wrapper if cls is None else wrapper(cls)
