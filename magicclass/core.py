from __future__ import annotations
from functools import wraps as functools_wraps
import inspect
from enum import Enum
from dataclasses import is_dataclass, _POST_INIT_NAME
import warnings

from .class_gui import (
    ClassGui, 
    MainWindowClassGui,
    ScrollableClassGui,
    ButtonClassGui, 
    CollapsibleClassGui,
    SplitClassGui,
    TabbedClassGui,
    StackedClassGui,
    ToolBoxClassGui,
    ListClassGui,
    )
from ._base import PopUpMode
from .menu_gui import ContextMenuGui, MenuGui, MenuGuiBase
from .macro import Expr
from .utils import check_collision, get_app

_BASE_CLASS_SUFFIX = "_Base"

class WidgetType(Enum):
    none = "none"
    scrollable = "scrollable"
    split = "split"
    collapsible = "collapsible"
    button = "button"
    toolbox = "toolbox"
    tabbed = "tabbed"
    stacked = "stacked"
    list = "list"
    mainwindow = "mainwindow"

_TYPE_MAP = {
    WidgetType.none: ClassGui,
    WidgetType.scrollable: ScrollableClassGui,
    WidgetType.split: SplitClassGui,
    WidgetType.collapsible: CollapsibleClassGui,
    WidgetType.button: ButtonClassGui,
    WidgetType.toolbox: ToolBoxClassGui,
    WidgetType.tabbed: TabbedClassGui,
    WidgetType.stacked: StackedClassGui,
    WidgetType.list: ListClassGui,
    WidgetType.mainwindow: MainWindowClassGui,
}

def magicclass(class_: type|None = None,
               *,
               layout: str = "vertical", 
               labels: bool = True, 
               name: str = None,
               close_on_run: bool = True,
               popup: bool = True,
               popup_mode: str | PopUpMode = PopUpMode.popup,
               widget_type: WidgetType | str = WidgetType.none,
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
    name : str
        Name of GUI.
    close_on_run : bool, default is True
        If True, magicgui created by every method will be deleted after the method is completed without
        exceptions, i.e. magicgui is more like a dialog.
    popup : bool, default is True
        If True, magicgui created by every method will be poped up, else they will be appended as a
        part of the main widget.
    widget_type : WidgetType or str, optional
        Widget type of container.
    parent : magicgui.widgets._base.Widget, optional
        Parent widget if exists.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    widget_type = WidgetType(widget_type)
    
    popup_mode = _popup_deprecation(popup, popup_mode)
    
    def wrapper(cls) -> ClassGui:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        
        class_gui = _TYPE_MAP[widget_type]
        
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
        
        @functools_wraps(oldclass.__init__)
        def __init__(self, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!
            macro_init = Expr.parse_init(self, cls, args, kwargs)
            class_gui.__init__(self, 
                               layout=layout,
                               parent=parent,
                               close_on_run=close_on_run, 
                               popup_mode=PopUpMode(popup_mode),
                               labels=labels,
                               name=name or cls.__name__.replace("_", " ")
                               )
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_attributes_into_widgets()
            
            if hasattr(self, _POST_INIT_NAME) and not is_dataclass(cls):
                self.__post_init__()
            
            # Record class instance construction
            self._recorded_macro.append(macro_init)
            if widget_type in (WidgetType.collapsible, WidgetType.button):
                self.btn_text = self.name

        newclass.__init__ = __init__
        
        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__
        
        return newclass
    
    return wrapper if class_ is None else wrapper(class_)


def magicmenu(class_: type = None, 
              *, 
              close_on_run: bool = True,
              popup: bool = True,
              popup_mode: str | PopUpMode = PopUpMode.popup,
              parent = None
              ):
    """
    Decorator that can convert a Python class into a menu bar.
                
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
    parent : magicgui.widgets._base.Widget, optional
        Parent widget if exists.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    return _call_magicmenu(class_, close_on_run, popup, popup_mode, parent, MenuGui)

def magiccontext(class_: type = None, 
                 *, 
                 close_on_run: bool = True,
                 popup: bool = True,
                 popup_mode: str | PopUpMode = PopUpMode.popup,
                 parent=None
                 ):
    """
    Decorator that can convert a Python class into a context menu.
                
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
    parent : magicgui.widgets._base.Widget, optional
        Parent widget if exists.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    return _call_magicmenu(class_, close_on_run, popup, popup_mode, parent, ContextMenuGui)


def _call_magicmenu(class_: type = None, 
                    close_on_run: bool = True,
                    popup: bool = True,
                    popup_mode: str | PopUpMode = PopUpMode.popup,
                    parent = None,
                    menugui_class: type[MenuGuiBase] = None,
                    ):
    
    popup_mode = _popup_deprecation(popup, popup_mode)
        
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first, PopUpMode.last):
        raise ValueError(f"Mode {popup_mode.value} is not compatible with Menu.")
    
    def wrapper(cls) -> menugui_class:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        
        check_collision(cls, menugui_class)
        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (menugui_class, oldclass), {})
        
        newclass.__signature__ = sig
        newclass.__doc__ = doc
                
        @functools_wraps(oldclass.__init__)
        def __init__(self, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!
            macro_init = Expr.parse_init(self, cls, args, kwargs)
            menugui_class.__init__(self, parent=parent, close_on_run=close_on_run,
                                   popup_mode=PopUpMode(popup_mode))
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

def _popup_deprecation(popup, popup_mode):
    if not popup:
        msg = "'popup' is deprecated. You can select popup mode from 'first', 'last', 'dock', 'above', " \
              "'below' or 'parentlast', and call this function like >>> @magicclass(popup_mode='first')"
        warnings.warn(msg, DeprecationWarning)
        return PopUpMode.parentlast
    else:
        return popup_mode