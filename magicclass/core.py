from __future__ import annotations
from functools import wraps as functools_wraps
import inspect
from enum import Enum
from dataclasses import is_dataclass
from typing import Any
import warnings
from typing_extensions import Annotated, _AnnotatedAlias

from magicclass.fields import MagicField, MISSING

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
from ._base import PopUpMode, ErrorMode, defaults
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

def Bound(value: Any) -> _AnnotatedAlias:
    """
    Make Annotated type from a MagicField or a method.
    """    
    # It is better to annotate like Annotated[int, {...}] but some widgets does not
    # support bind. Also, we must ensure that parameters annotated with "bind" creates
    # EmptyWidget.
    
    return Annotated[Any, {"bind": value}]

def magicclass(class_: type|None = None,
               *,
               layout: str = "vertical", 
               labels: bool = True, 
               name: str = None,
               close_on_run: bool = None,
               popup: bool = True,
               popup_mode: str | PopUpMode = None,
               error_mode: str | ErrorMode = None,
               widget_type: str | WidgetType = WidgetType.none,
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
        Deprecated.
    popup_mode : str or PopUpMode, default is PopUpMode.popup
        Option of how to popup FunctionGui widget when a button is clicked.
    error_mode : str or ErrorMode, default is ErrorMode.msgbox
        Option of how to raise errors during function calls.
    widget_type : WidgetType or str, optional
        Widget type of container.
    parent : magicgui.widgets._base.Widget, optional
        Parent widget if exists.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    if popup_mode is None:
        popup_mode = defaults["popup_mode"]
    if close_on_run is None:
        close_on_run = defaults["close_on_run"]
    if error_mode is None:
        error_mode = defaults["error_mode"]
        
    widget_type = WidgetType(widget_type)
    
    popup_mode = _popup_deprecation(popup, popup_mode)
    
    def wrapper(cls) -> ClassGui:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        elif is_dataclass(cls):
            raise TypeError("dataclass is not compatible with magicclass.")
        
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
                               error_mode=ErrorMode(error_mode),
                               labels=labels,
                               name=name or cls.__name__.replace("_", " ")
                               )
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_attributes_into_widgets()
            
            if hasattr(self, "__post_init__"):
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
              close_on_run: bool = None,
              popup: bool = True,
              popup_mode: str | PopUpMode = None,
              error_mode: str | ErrorMode = None,
              parent = None
              ):
    """
    Decorator that can convert a Python class into a menu bar.
    """    
    return _call_magicmenu(**locals(), menugui_class=MenuGui)

def magiccontext(class_: type = None, 
                 *, 
                 close_on_run: bool = None,
                 popup: bool = True,
                 popup_mode: str | PopUpMode = None,
                 error_mode: str | ErrorMode = None,
                 parent=None
                 ):
    """
    Decorator that can convert a Python class into a context menu.
    """    
    return _call_magicmenu(**locals(), menugui_class=ContextMenuGui)


def _call_magicmenu(class_: type = None, 
                    close_on_run: bool = True,
                    popup: bool = True,
                    popup_mode: str | PopUpMode = None,
                    error_mode: str | ErrorMode = None,
                    parent = None,
                    menugui_class: type[MenuGuiBase] = None,
                    ):
    """
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

    if popup_mode is None:
        popup_mode = defaults["popup_mode"]
    if close_on_run is None:
        close_on_run = defaults["close_on_run"]
    if error_mode is None:
        error_mode = defaults["error_mode"]
        
    popup_mode = _popup_deprecation(popup, popup_mode)
        
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first, PopUpMode.last):
        raise ValueError(f"Mode {popup_mode.value} is not compatible with Menu.")
    
    def wrapper(cls) -> menugui_class:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        elif is_dataclass(cls):
            raise TypeError("dataclass is not compatible with magicclass.")
        
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
            menugui_class.__init__(self, 
                                   parent=parent,
                                   close_on_run=close_on_run,
                                   popup_mode=PopUpMode(popup_mode),
                                   error_mode=ErrorMode(error_mode),
                                   )
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_attributes_into_widgets()
            
            if hasattr(self, "__post_init__"):
                self.__post_init__()
            
            # Record class instance construction
            self._recorded_macro.append(macro_init)

        newclass.__init__ = __init__
        
        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__
        
        return newclass
    
    return wrapper if class_ is None else wrapper(class_)

magicmenu.__doc__ += _call_magicmenu.__doc__
magiccontext.__doc__ += _call_magicmenu.__doc__

def _popup_deprecation(popup, popup_mode):
    if not popup:
        msg = "'popup' is deprecated. You can select popup mode from 'first', 'last', 'dock', 'above', " \
              "'below' or 'parentlast', and call this function like >>> @magicclass(popup_mode='first')"
        warnings.warn(msg, DeprecationWarning)
        return PopUpMode.parentlast
    else:
        return popup_mode

class _CallableClass:
    def __init__(self):
        self.__name__ = self.__class__.__name__
        self.__qualname__ = self.__class__.__qualname__
    
    def __call__(self, *args, **kwargs):
        raise NotImplementedError()
    
    
class Parameters(_CallableClass):
    def __init__(self):
        super().__init__()
        
        sig = [inspect.Parameter(name="self", 
                                 kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        for name, attr in inspect.getmembers(self):
            if name.startswith("__") or callable(attr):
                continue
            sig.append(inspect.Parameter(name=name, 
                                         kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                         default=attr)
                           )
        if hasattr(self.__class__, "__annotations__"):
            annot = self.__class__.__annotations__
            for name, t in annot.items():
                sig.append(inspect.Parameter(name=name, 
                                             kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                             annotation=t))
        
        self.__signature__ = inspect.Signature(sig)
        
    def __call__(self, *args):
        params = list(self.__signature__.parameters.keys())[1:]
        for a, param in zip(args, params):
            setattr(self, param, a)

class Info(_CallableClass):
    def __call__(self):
        from .widgets import ConsoleTextEdit
        from .utils import extract_tooltip
        win = ConsoleTextEdit(name="macro")
        win.read_only = True
        win.value = extract_tooltip(self.__class__)
        win.show()
        return None
    