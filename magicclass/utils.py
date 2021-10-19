from __future__ import annotations
import inspect
from dataclasses import _FIELDS
from functools import wraps
from typing import Callable, Iterator, Any, TYPE_CHECKING
from docstring_parser import parse
from qtpy.QtWidgets import QApplication, QMessageBox


if TYPE_CHECKING:
    from magicgui.widgets._bases import Widget
    from magicgui.widgets import FunctionGui
    import napari
    from .field import MagicField

APPLICATION = None

def iter_members(cls: type, exclude_prefix: str = "__") -> Iterator[str]:
    """
    Iterate over all the members in the order of source code line number. 
    """    
    members = getmembers(cls, exclude_prefix)
    fields: dict[str, MagicField] = getattr(cls, _FIELDS, {})

    return members + list(fields.items())

def check_collision(cls0: type, cls1: type):
    """
    Check if two classes have name collisions.
    """    
    mem0 = set(x[0] for x in iter_members(cls0))
    mem1 = set(x[0] for x in iter_members(cls1))
    collision = mem0 & mem1
    if collision:
        raise AttributeError(f"Collision between {cls0.__name__} and {cls1.__name__}: {collision}")


def getmembers(object: type, exclude_prefix: str):
    """
    This function is identical to inspect.getmembers except for the order
    of the results. We have to sort the name in the order of line number.
    """    
    mro = (object,) + inspect.getmro(object)
    results = []
    processed = set()
    names: list[str] = list(object.__dict__.keys())
    try:
        for base in mro:
            for k in base.__dict__.keys():
                if k not in names:
                    names.append(k)
                    
    except AttributeError:
        pass
    
    for key in names:
        try:
            value = getattr(object, key)
            # handle the duplicate key
            if key in processed:
                raise AttributeError
        except AttributeError:
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            else:
                continue
        if not key.startswith(exclude_prefix):
            results.append((key, value))
        processed.add(key)
    
    return results

def n_parameters(func: Callable):
    """
    Count the number of parameters of a callable object.
    """    
    return len(inspect.signature(func).parameters)

def extract_tooltip(obj: Any) -> str:
    if not hasattr(obj, "__doc__"):
        return ""
    
    doc = parse(obj.__doc__)
    if doc.short_description is None:
        return ""
    elif doc.long_description is None:
        return doc.short_description
    else:
        return doc.short_description + "\n" + doc.long_description

def raise_error_msg(parent, title: str = "Error", msg: str = "error"):
    QMessageBox.critical(parent, title, msg, QMessageBox.Ok)
    return None

def raise_error_in_msgbox(_func, parent: Widget = None):
    @wraps(_func)
    def wrapped_func(*args, **kwargs):
        try:
            out = _func(*args, **kwargs)
        except Exception as e:
            QMessageBox.critical(parent.native, e.__class__.__name__, str(e), QMessageBox.Ok)
            out = e
        return out
    
    return wrapped_func

def get_parameters(fgui: FunctionGui):
    inputs = {param: fgui[param].value
              for param in fgui.__signature__.parameters.keys()
              }
    return inputs

def define_callback(self, callback: Callable):
    clsname, funcname = callback.__qualname__.split(".")
    def _callback():
        # search for parent instances that have the same name.
        current_self = self
        while not (hasattr(current_self, funcname) and 
                    current_self.__class__.__name__ == clsname):
            current_self = current_self.__magicclass_parent__
        getattr(current_self, funcname)()
        return None
    return _callback

def show_mgui(mgui: FunctionGui):
    try:
        viewer = mgui.parent.parent().qt_viewer.viewer
    except AttributeError:
        mgui.show()
        mgui.native.activateWindow()
    else:
        viewer.window._dock_widgets[mgui.parent.objectName()].show()
    return None
    

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
