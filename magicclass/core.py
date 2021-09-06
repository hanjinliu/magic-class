from __future__ import annotations
from functools import wraps
from .basegui import BaseGui

def magicclass(cls:type|None=None, parent=None):
    """
    Decorator that can convert a Python class into a QWidget with push buttons.
    
    >>> @magicclass
    >>> class C:
    >>>     ...
    >>> c = C(a=0)
    >>> c.show()
    
    >>> @magicclass
    >>> class Reader:
    >>>     def load(self, path:Path):
    >>>         self.data = pd.read_csv(path)
    >>>     
    >>>     def save(self, path:Path):
    >>>         self.data.to_csv(path)
            

    Parameters
    ----------
    cls : type, optional
        Class to be decorated.
    parent : QWidget, optional
        Parent widget, if needed.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    def wrapper(cls):
        oldclass = type(cls.__name__ + "_Base", (cls,), {})
        newclass = type(cls.__name__, (oldclass, BaseGui), {})
        
        @wraps(oldclass.__init__)
        def __init__(self, *args, **kwargs):
            super(oldclass, self).__init__(*args, **kwargs)
            BaseGui.__init__(self, parent=parent)
            self.setObjectName(oldclass.__name__)
            self._convert_methods_into_widgets()
            
        setattr(newclass, "__init__", __init__)
        return newclass
    
    return wrapper if cls is None else wrapper(cls)
