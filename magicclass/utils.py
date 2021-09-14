from __future__ import annotations
from functools import wraps
from itertools import chain
import inspect
import sys
from typing import Callable, Iterable
from qtpy.QtWidgets import QApplication

APPLICATION = None

def iter_members_and_annotations(cls:type, exclude_prefix:str="_") -> Iterable[str]:
    # All the class members
    members = filter(lambda x: not x[0].startswith(exclude_prefix),
                     inspect.getmembers(cls)
                     )
    
    # All the class annotations
    cls_annotations = filter(lambda x: not x[0].startswith(exclude_prefix),
                             getattr(cls, "__annotations__", {}).items()
                             )
    attrs = chain(members, cls_annotations)

    return map(lambda x: x[0], sorted(attrs, key=get_line_number))
    

def check_collision(cls0:type, cls1:type):
    """
    Check if two classes have name collisions.
    """    
    mem0 = set(iter_members_and_annotations(cls0, exclude_prefix="__"))
    mem1 = set(iter_members_and_annotations(cls1, exclude_prefix="__"))
    collision = mem0 & mem1
    if collision:
        raise AttributeError(f"Collision: {collision}")

def get_line_number(member) -> int:
    """
    Get the line number of a member function or inner class in the source code.
    """    
    n = -1
    obj = member[1]
    if not isinstance(obj, type):
        if hasattr(obj, "_function_line_number"):
            n = obj._function_line_number
        else:
            try:
                original_func = getattr(obj, "__wrapped__", obj)
                n = original_func.__code__.co_firstlineno
            except AttributeError:
                pass
    else:
        n = getattr(obj, "_class_line_number", -1)

    return n

def current_location(depth:int=0):
    """
    Get the current location in the source code.
    """    
    frame = sys._getframe(depth)
    return frame.f_lineno

def inline_base(obj:type|Callable, name:str=None, _depth:int=3, **kwargs):
    if name is None:
        name = obj.__name__

    if isinstance(obj, type):
        class _class(obj):
            def __init__(self):
                super().__init__(**kwargs)
                self.name = name
            
        obj = _class
        obj._class_line_number = current_location(_depth)
        
    elif callable(obj):
        # Function must be defined again. Deep copy did not work.
        @wraps(obj)
        def _f(*args, **kwargs):
            return obj(*args, **kwargs)
        obj = _f
        obj._function_line_number = current_location(_depth)
    else:
        raise TypeError(f"Can only re-define function or class, not {type(obj)}")
    
    obj.__name__ = name
    return obj

def inline(obj:type|Callable, name:str=None, **kwargs):
    """
    Inline definition of classes or functions. This function is important when you want
    to define a class or member function outside a magic-class while keep the widget
    order sorted by the order of source code. 

    Parameters
    ----------
    obj : type or callable
        The object to be inline-defined.
    name : str, optional
        Name of the inlined object. This argument is useful when a same class or function
        is inlined for several times.
    **kwargs : other keyword arguments of constructor.
    """    
    return inline_base(obj, name=name, **kwargs)

def gui_qt():
    """
    Call "%gui qt" magic,
    """    
    try:
        from IPython import get_ipython
    except ImportError:
        get_ipython = lambda: False

    shell = get_ipython()
    
    if shell and shell.active_eventloop != "qt":
        shell.enable_gui("qt")
    return None

def get_app():
    """
    Get QApplication. This is important when using Jupyter.
    """    
    gui_qt()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    global APPLICATION
    APPLICATION = app
    return app
