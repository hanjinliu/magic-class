from __future__ import annotations
from functools import wraps
import inspect
from dataclasses import is_dataclass, _POST_INIT_NAME
from .class_gui import (
    ClassGui, 
    MainWindowClassGui,
    ScrollableClassGui,
    ButtonClassGui, 
    CollapsibleClassGui,
    TabbedClassGui,
    ToolBoxClassGui,
    )
from .menu_gui import MenuGui
from .macro import Expr
from .utils import check_collision, get_app

_BASE_CLASS_SUFFIX = "_Base"

def magicclass(class_: type|None = None,
               *,
               layout: str = "vertical", 
               labels: bool = True, 
               close_on_run: bool = True,
               popup: bool = True,
               result_widget: bool = False, 
               single_call: bool = True, 
               widget_type: str = None,
               parent = None
               ) -> ClassGui:
    """
    Decorator that can convert a Python class into a widget.
    
    >>> @magicclass
    >>> class C:
    >>>     ...
    >>> c = C(a=0)
    >>> c.show()
            
    Parameters
    ----------
    class_ : type, optional
        Class to be decorated.
    layout : str, "vertical" or "horizontal", default is "vertical"
        Layout of the main widget.
    labels : bool, default is True
        If true, magicgui labels are shown.
    close_on_run : bool, default is True
        If True, magicgui created by every method will be deleted after the method is completed without
        exceptions, i.e. magicgui is more like a dialog.
    popup : bool, default is True
        If True, magicgui created by every method will be poped up, else they will be appended as a
        part of the main widget.
    result_widget : bool, default is False
        If true, FunctionGui-like results widget will be added.
    single_call : bool, default is True 
        If true, user cannot call the same function at the same time. If same button is clicked, the 
        existing magicgui window is re-activated.
    widget_type : str, optional
        Widget type of container.
    parent : magicgui.widgets._base.Widget, optional
        Parent widget if exists.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    def wrapper(cls) -> ClassGui:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        if widget_type is None:
            class_gui = ClassGui
        elif widget_type == "scrollable":
            class_gui = ScrollableClassGui
        elif widget_type == "collapsible":
            class_gui = CollapsibleClassGui
        elif widget_type == "button":
            class_gui = ButtonClassGui
        elif widget_type == "toolbox":
            class_gui = ToolBoxClassGui
        elif widget_type == "tabbed":
            class_gui = TabbedClassGui
        elif widget_type == "mainwindow":
            class_gui = MainWindowClassGui
        else:
            raise ValueError(widget_type)
        
        check_collision(cls, class_gui)
        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        annot = cls.__dict__.get("__annotations__", {})
        
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (class_gui, oldclass), {})
        
        newclass.__signature__ = sig
        newclass.__doc__ = doc
        
        # concatenate annotations
        newclass.__annotations__ = class_gui.__annotations__.copy()
        newclass.__annotations__.update(annot)
        
        @wraps(oldclass.__init__)
        def __init__(self, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!
            macro_init = Expr.parse_init(cls, args, kwargs)
            class_gui.__init__(self, layout=layout, parent=parent, close_on_run=close_on_run, 
                              popup=popup, labels=labels, result_widget=result_widget,
                              name=cls.__name__.replace("_", " "), single_call=single_call)
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_attributes_into_widgets()
            
            if hasattr(self, _POST_INIT_NAME) and not is_dataclass(cls):
                self.__post_init__()
            
            # Record class instance construction
            self._recorded_macro.append(macro_init)
            if widget_type in ("collapsible", "button"):
                self.btn_text = self.__class__.__name__

        newclass.__init__ = __init__
        
        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__
        
        return newclass
    
    return wrapper if class_ is None else wrapper(class_)


def magicmenu(class_: type = None, 
              *, 
              close_on_run: bool = True,
              popup: bool = True,
              single_call: bool = True,
              parent=None
              ):
    """
    Decorator that can convert a Python class into a widget.
    
    >>> @magicclass
    >>> class C:
    >>>     ...
    >>> c = C(a=0)
    >>> c.show()
            
    Parameters
    ----------
    class_ : type, optional
        Class to be decorated.
    close_on_run : bool, default is True
        If True, magicgui created by every method will be deleted after the method is completed without
        exceptions, i.e. magicgui is more like a dialog.
    popup : bool, default is True
        If True, magicgui created by every method will be poped up, else they will be appended as a
        part of the main widget.
    single_call : bool, default is True 
        If true, user cannot call the same function at the same time. If same button is clicked, the 
        existing magicgui window is re-activated.
    parent : magicgui.widgets._base.Widget, optional
        Parent widget if exists.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    def wrapper(cls) -> MenuGui:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        
        check_collision(cls, MenuGui)
        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (MenuGui, oldclass), {})
        
        newclass.__signature__ = sig
        newclass.__doc__ = doc
                
        @wraps(oldclass.__init__)
        def __init__(self, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!
            macro_init = Expr.parse_init(cls, args, kwargs)
            MenuGui.__init__(self, parent=parent, close_on_run=close_on_run, popup=popup, 
                             single_call=single_call)
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_attributes_into_widgets()
            
            if hasattr(self, _POST_INIT_NAME) and not is_dataclass(cls):
                self.__post_init__()
            
            # Record class instance construction
            self._recorded_macro.append(macro_init)

        newclass.__init__ = __init__
        
        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__
        
        return newclass
    
    return wrapper if class_ is None else wrapper(class_)

