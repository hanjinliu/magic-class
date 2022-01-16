from __future__ import annotations
from functools import wraps as functools_wraps
import inspect
from dataclasses import is_dataclass
from weakref import WeakValueDictionary
from typing import Any
from typing_extensions import Annotated, _AnnotatedAlias

from .gui.class_gui import (
    ClassGuiBase, 
    ClassGui,
    FrameClassGui,
    GroupBoxClassGui,
    MainWindowClassGui,
    SubWindowsClassGui,
    ScrollableClassGui,
    DraggableClassGui,
    ButtonClassGui, 
    CollapsibleClassGui,
    HCollapsibleClassGui,
    SplitClassGui,
    TabbedClassGui,
    StackedClassGui,
    ToolBoxClassGui,
    ListClassGui,
    )
from .gui._base import PopUpMode, ErrorMode, defaults, MagicTemplate, check_override
from .gui import ContextMenuGui, MenuGui, MenuGuiBase, ToolBarGui
from ._app import get_app
from ._typing import WidgetType, WidgetTypeStr, PopUpModeStr, ErrorModeStr
from . import _macrokit  # activate macrokit registration things.
    
_BASE_CLASS_SUFFIX = "_Base"
_POST_INIT = "__post_init__"

_TYPE_MAP = {
    WidgetType.none: ClassGui,
    WidgetType.scrollable: ScrollableClassGui,
    WidgetType.draggable: DraggableClassGui,
    WidgetType.split: SplitClassGui,
    WidgetType.collapsible: CollapsibleClassGui,
    WidgetType.hcollapsible: HCollapsibleClassGui,
    WidgetType.button: ButtonClassGui,
    WidgetType.toolbox: ToolBoxClassGui,
    WidgetType.tabbed: TabbedClassGui,
    WidgetType.stacked: StackedClassGui,
    WidgetType.list: ListClassGui,
    WidgetType.groupbox: GroupBoxClassGui,
    WidgetType.frame: FrameClassGui,
    WidgetType.subwindows: SubWindowsClassGui,
    WidgetType.mainwindow: MainWindowClassGui,
}

def Bound(value: Any) -> _AnnotatedAlias:
    """
    Make Annotated type from a MagicField or a method, such as:
    
    .. code-block:: python
        
        from magicclass import magicclass, field
        
        @magicclass
        class MyClass:
            i = field(int)
            def func(self, v: Bound(i)):
                ...
    
    ``Bound(value)`` is identical to ``Annotated[Any, {"bind": value}]``.    
    """    
    # It is better to annotate like Annotated[int, {...}] but some widgets does not
    # support bind. Also, we must ensure that parameters annotated with "bind" creates
    # EmptyWidget.
    
    return Annotated[Any, {"bind": value}]


def magicclass(class_: type | None = None,
               *,
               layout: str = "vertical", 
               labels: bool = True, 
               name: str = None,
               visible: bool | None = None,
               close_on_run: bool = None,
               popup_mode: PopUpModeStr | PopUpMode = None,
               error_mode: ErrorModeStr | ErrorMode = None,
               widget_type: WidgetTypeStr | WidgetType = WidgetType.none,
               icon_path: str = None,
               parent = None
               ):
    """
    Decorator that can convert a Python class into a widget.
    
    .. code-block:: python
    
        @magicclass
        class C:
            ...
        ui = C()
        ui.show()  # open GUI
            
    Parameters
    ----------
    class_ : type, optional
        Class to be decorated.
    layout : str, "vertical" or "horizontal", default is "vertical"
        Layout of the main widget.
    labels : bool, default is True
        If true, magicgui labels are shown.
    name : str, optional
        Name of GUI.
    visible : bool, optional
        Initial visibility of GUI. Useful when magic class is nested.
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
    icon_path : str, optional
        Path to the icon image.
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
    
    if isinstance(widget_type, str):
        widget_type = widget_type.lower()
        
    widget_type = WidgetType(widget_type)
    
    def wrapper(cls) -> type[ClassGui]:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        elif is_dataclass(cls):
            raise TypeError("dataclass is not compatible with magicclass.")
        
        class_gui = _TYPE_MAP[widget_type]
        
        if not issubclass(cls, MagicTemplate):
            check_override(cls)
        
        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        annot = cls.__dict__.get("__annotations__", {})
        mod = cls.__module__
        qualname = cls.__qualname__
        
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (class_gui, oldclass), {})
        
        newclass.__signature__ = sig
        newclass.__doc__ = doc
        newclass.__module__ = mod
        newclass.__qualname__ = qualname
        
        # concatenate annotations
        newclass.__annotations__ = class_gui.__annotations__.copy()
        newclass.__annotations__.update(annot)
        
        @functools_wraps(oldclass.__init__)
        def __init__(self: MagicTemplate, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!
            
            class_gui.__init__(self, 
                               layout=layout,
                               parent=parent,
                               close_on_run=close_on_run, 
                               popup_mode=PopUpMode(popup_mode),
                               error_mode=ErrorMode(error_mode),
                               labels=labels,
                               name=name or cls.__name__.replace("_", " "),
                               visible=visible,
                               )
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_attributes_into_widgets()
            
            if hasattr(self, _POST_INIT):
                self.__post_init__()
            
            if widget_type in (WidgetType.collapsible, WidgetType.button):
                self.btn_text = self.name
            
            macrowidget = self.macro.widget.native
            macrowidget.setParent(self.native, macrowidget.windowFlags())
            self.macro.widget.__magicclass_parent__ = self
            
            if icon_path:
                self.icon_path = icon_path

        newclass.__init__ = __init__
        
        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__
        
        return newclass

    if class_ is None:
        return wrapper
    else:
        return wrapper(class_)


def magicmenu(class_: type = None, 
              *, 
              close_on_run: bool = None,
              popup_mode: str | PopUpMode = None,
              error_mode: str | ErrorMode = None,
              labels: bool = True, 
              icon_path: str = None,
              parent = None
              ):
    """
    Decorator that can convert a Python class into a menu bar.
    """    
    return _call_magicmenu(**locals(), menugui_class=MenuGui)


def magiccontext(class_: type = None, 
                 *, 
                 close_on_run: bool = None,
                 popup_mode: str | PopUpMode = None,
                 error_mode: str | ErrorMode = None,
                 labels: bool = True, 
                 icon_path: str = None,
                 parent=None
                 ):
    """
    Decorator that can convert a Python class into a context menu.
    """    
    return _call_magicmenu(**locals(), menugui_class=ContextMenuGui)


def magictoolbar(class_: type = None, 
                 *, 
                 close_on_run: bool = None,
                 popup_mode: str | PopUpMode = None,
                 error_mode: str | ErrorMode = None,
                 labels: bool = True, 
                 icon_path: str = None,
                 parent = None
                 ):
    """
    Decorator that can convert a Python class into a menu bar.
    """    
    return _call_magicmenu(**locals(), menugui_class=ToolBarGui)


class MagicClassFactory:
    """
    Factory class that can make any magic-class.
    """    
    def __init__(self, 
                 name: str,
                 layout: str = "vertical", 
                 labels: bool = True, 
                 close_on_run: bool = None,
                 popup_mode: str | PopUpMode = None,
                 error_mode: str | ErrorMode = None,
                 widget_type: str | WidgetType = WidgetType.none,
                 icon_path: str = None,
                 parent = None,
                 attrs: dict[str] = None
                 ):
        self.name = name
        self.layout = layout
        self.labels = labels
        self.close_on_run = close_on_run
        self.popup_mode = popup_mode
        self.error_mode = error_mode
        self.widget_type = widget_type
        self.icon_path = icon_path
        self.parent = parent
        self.attrs = attrs
    
    def as_magicclass(self) -> ClassGuiBase:
        _cls = type(self.name, (), self.attrs)
        cls = magicclass(_cls, layout=self.layout, labels=self.labels, close_on_run=self.close_on_run, 
                         name=self.name, popup_mode=self.popup_mode, error_mode=self.error_mode,
                         widget_type=self.widget_type, icon_path=self.icon_path, parent=self.parent)
        return cls
    
    def as_magictoolbar(self) -> ToolBarGui:
        _cls = type(self.name, (), self.attrs)
        cls = magictoolbar(_cls, close_on_run=self.close_on_run, popup_mode=self.popup_mode, 
                           error_mode=self.error_mode, labels=self.labels, icon_path=self.icon_path,
                           parent=self.parent)
        return cls   
    
    def as_magicmenu(self) -> MenuGui:
        _cls = type(self.name, (), self.attrs)
        cls = magicmenu(_cls, close_on_run=self.close_on_run, popup_mode=self.popup_mode, 
                        error_mode=self.error_mode, labels=self.labels, icon_path=self.icon_path,
                        parent=self.parent)
        return cls
    
    def as_magiccontext(self) -> ContextMenuGui:
        _cls = type(self.name, (), self.attrs)
        cls = magiccontext(_cls, close_on_run=self.close_on_run, popup_mode=self.popup_mode, 
                           error_mode=self.error_mode, labels=self.labels, icon_path=self.icon_path,
                           parent=self.parent)
        return cls


def _call_magicmenu(class_: type = None, 
                    close_on_run: bool = True,
                    popup_mode: str | PopUpMode = None,
                    error_mode: str | ErrorMode = None,
                    labels: bool = True, 
                    icon_path: str = None,
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
        
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first, PopUpMode.last):
        raise ValueError(f"Mode {popup_mode.value} is not compatible with Menu.")
    
    def wrapper(cls) -> type[menugui_class]:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        elif is_dataclass(cls):
            raise TypeError("dataclass is not compatible with magicclass.")
        
        if not issubclass(cls, MagicTemplate):
            check_override(cls)
            
        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        mod = cls.__module__
        qualname = cls.__qualname__
        
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (menugui_class, oldclass), {})
        
        newclass.__signature__ = sig
        newclass.__doc__ = doc
        newclass.__module__ = mod
        newclass.__qualname__ = qualname
                
        @functools_wraps(oldclass.__init__)
        def __init__(self: MagicTemplate, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!

            menugui_class.__init__(self, 
                                   parent=parent,
                                   close_on_run=close_on_run,
                                   popup_mode=PopUpMode(popup_mode),
                                   error_mode=ErrorMode(error_mode),
                                   labels=labels, 
                                   )
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_attributes_into_widgets()
            
            if hasattr(self, _POST_INIT):
                self.__post_init__()
            
            if icon_path:
                self.icon_path = icon_path
            
            macrowidget = self.macro.widget.native
            macrowidget.setParent(self.native, macrowidget.windowFlags())
            self.macro.widget.__magicclass_parent__ = self

        newclass.__init__ = __init__
        
        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__
        
        return newclass
    
    return wrapper if class_ is None else wrapper(class_)

magicmenu.__doc__ += _call_magicmenu.__doc__
magiccontext.__doc__ += _call_magicmenu.__doc__

_HELPS: WeakValueDictionary[int, MagicTemplate] = WeakValueDictionary()

def build_help(ui: MagicTemplate, parent=None):
    """
    Build a widget for user guide. Once it is built, widget will be cached.

    Parameters
    ----------
    ui : MagicTemplate
        Magic class UI object.

    Returns
    -------
    HelpWidget
        Help of the input UI.
    """    
    ui_id = id(ui)
    if ui_id in _HELPS.keys():
        help_widget = _HELPS[ui_id]
    else:
        from .help import HelpWidget
        if parent is None:
            parent = ui.native
        help_widget = HelpWidget(ui, parent=parent)
        _HELPS[ui_id] = help_widget
    return help_widget


class Parameters:
    def __init__(self):
        self.__name__ = self.__class__.__name__
        self.__qualname__ = self.__class__.__qualname__
        
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
        
    def __call__(self, *args) -> None:
        params = list(self.__signature__.parameters.keys())[1:]
        for a, param in zip(args, params):
            setattr(self, param, a)

    def as_dict(self) -> dict[str, Any]:
        """
        Convert parameter fields into a dictionary.
        
        .. code-block:: python
        
            class params(Parameters):
                i = 1
                j = 2
            
            p = params()
            p.as_dict() # {"i": 1, "j": 2}
            
        """        
        params = list(self.__signature__.parameters.keys())[1:]
        return {param: getattr(self, param) for param in params}
