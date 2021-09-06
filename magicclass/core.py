from __future__ import annotations
from functools import wraps
from .basegui import BaseGui
from .utils import check_collision

def magicclass(cls:type|None=None, layout:str="vertical", close_on_run:bool=True):
    """
    Decorator that can convert a Python class into a QWidget with push buttons.
    
    >>> @magicclass
    >>> class C:
    >>>     ...
    >>> c = C(a=0)
    >>> c.show()
    
    >>> from pathlib import Path
    >>>
    >>> @magicclass
    >>> class Reader:
    >>>     def load(self, path:Path):
    >>>         self.data = pd.read_csv(path)
    >>>     
    >>>     def save(self, path:str):
    >>>         self.data.to_csv(path)
            

    Parameters
    ----------
    cls : type, optional
        Class to be decorated.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    def wrapper(cls):
        check_collision(cls, BaseGui)
        oldclass = type(cls.__name__ + "_Base", (cls,), {})
        newclass = type(cls.__name__, (oldclass, BaseGui), {})
        newclass.__doc__ = cls.__doc__
        
        @wraps(oldclass.__init__)
        def __init__(self, *args, **kwargs):
            super(oldclass, self).__init__(*args, **kwargs)
            BaseGui.__init__(self, layout=layout, close_on_run=close_on_run, name=oldclass.__name__)
            self._convert_methods_into_widgets()
            
        setattr(newclass, "__init__", __init__)
        return newclass
    
    return wrapper if cls is None else wrapper(cls)
