from __future__ import annotations
from typing import Callable
import warnings
from inspect import signature
from magicgui.widgets import Image, Table, Label, FunctionGui
from magicgui.widgets._bases import ButtonWidget
from magicgui.widgets._bases.widget import Widget
from macrokit import Symbol
from qtpy.QtWidgets import QMenu

from .mgui_ext import AbstractAction, WidgetAction, _LabeledWidgetAction
from ._base import BaseGui, PopUpMode, ErrorMode, ContainerLikeGui, nested_function_gui_callback
from .utils import MagicClassConstructionError

from ..signature import get_additional_option
from ..fields import MagicField
from ..widgets import Separator, FreeWidget
from ..utils import iter_members


def _check_popupmode(popup_mode: PopUpMode):
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first):
        msg = f"magicmenu does not support popup mode {popup_mode.value}."\
                "PopUpMode.popup is used instead"
        warnings.warn(msg, UserWarning)
    elif popup_mode == PopUpMode.last:
        msg = f"magicmenu does not support popup mode {popup_mode.value}."\
                "PopUpMode.parentlast is used instead"
        warnings.warn(msg, UserWarning)
        popup_mode = PopUpMode.parentlast
    
    return popup_mode


class MenuGuiBase(ContainerLikeGui):
    def __init__(self, 
                 parent=None, 
                 name: str = None,
                 close_on_run: bool = None,
                 popup_mode: str|PopUpMode = None,
                 error_mode: str|ErrorMode = None,
                 labels: bool = True
                 ):
        popup_mode = _check_popupmode(popup_mode)
            
        super().__init__(close_on_run=close_on_run, popup_mode=popup_mode, error_mode=error_mode)
        name = name or self.__class__.__name__
        self.native = QMenu(name, parent)
        self.native.setToolTipsVisible(True)
        self.name = name
        self._list: list[MenuGuiBase | AbstractAction] = []
        self.labels = labels
       
    def _convert_attributes_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)
            
        # Bind all the methods and annotations
        base_members = set(x[0] for x in iter_members(MenuGuiBase))        
        
        _hist: list[tuple[str, str, str]] = [] # for traceback
        
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            try:
                if isinstance(attr, type):
                    if not issubclass(attr, BaseGui):
                        continue
                    # Nested magic-menu
                    widget = attr()
                    object.__setattr__(self, name, widget)
                
                elif isinstance(attr, MagicField):
                    widget = self._create_widget_from_field(name, attr)
                    
                else:
                    # convert class method into instance method
                    widget = getattr(self, name, None)
                    
                if name.startswith("_"):
                    continue
                
                if isinstance(widget, FunctionGui):
                    p0 = list(signature(attr).parameters)[0]
                    getattr(widget, p0).bind(self) # set self to the first argument
                
                elif isinstance(widget, BaseGui):
                    widget.__magicclass_parent__ = self
                    self.__magicclass_children__.append(widget)
                    widget._my_symbol = Symbol(name)
                    
                    if isinstance(widget, MenuGuiBase):
                        widget.native.setParent(self.native, widget.native.windowFlags())
                    
                    else:
                        widget = WidgetAction(widget)
                        
                elif isinstance(widget, Widget):
                    widget = WidgetAction(widget)

                if isinstance(widget, (MenuGuiBase, AbstractAction, Callable, Widget)):
                    if (not isinstance(widget, Widget)) and callable(widget):
                        widget = self._create_widget_from_method(widget)
                    
                    elif hasattr(widget, "__magicclass_parent__") or \
                        hasattr(widget.__class__, "__magicclass_parent__"):
                        if isinstance(widget, BaseGui):
                            widget._my_symbol = Symbol(name)
                        # magic-class has to know its parent.
                        # if __magicclass_parent__ is defined as a property, hasattr must be called
                        # with a type object (not instance).
                        widget.__magicclass_parent__ = self
                        
                    clsname = get_additional_option(attr, "into")
                    if clsname is not None:
                        self._unwrap_method(clsname, name, widget)
                    else:           
                        self._fast_insert(len(self), widget)
                    
                    _hist.append((name, str(type(attr)), type(widget).__name__))
            
            except Exception as e:
                hist_str = "\n\t".join(map(
                    lambda x: f"{x[0]} {x[1]} -> {x[2]}",
                    _hist
                    )) + f"\n\t\t{name} ({type(attr).__name__}) <--- Error"
                if not hist_str.startswith("\n\t"):
                    hist_str = "\n\t" + hist_str
                if isinstance(e, MagicClassConstructionError):
                    e.args = (f"\n{hist_str}\n{e}",)
                    raise e
                else:
                    raise MagicClassConstructionError(f"{hist_str}\n\n{type(e).__name__}: {e}") from e
        
        self._unify_label_widths()
        return None
    
    
    def _fast_insert(self, key: int, obj: Callable | MenuGuiBase | AbstractAction) -> None:
        if isinstance(obj, Callable):
            # Sometimes uses want to dynamically add new functions to GUI.
            if isinstance(obj, FunctionGui):
                if obj.parent is None:
                    f = nested_function_gui_callback(self, obj)
                    obj.called.connect(f)
            else:
                obj = self._create_widget_from_method(obj)
            
        if isinstance(obj, (self._component_class, MenuGuiBase)):
            insert_action_like(self.native, key, obj.native)
            self._list.insert(key, obj)
        
        elif isinstance(obj, WidgetAction):
            from .toolbar import ToolBarGui
            if isinstance(obj.widget, Separator):
                insert_action_like(self.native, key, "sep")
            
            elif isinstance(obj.widget, ToolBarGui):
                qmenu = QMenu(obj.widget.name, self.native)
                qmenu.addAction(obj.native)
                if obj.widget._icon_path is not None:
                    qmenu.setIcon(obj.widget.native.windowIcon())
                insert_action_like(self.native, key, qmenu)
                
            else:
                _hide_labels = (_LabeledWidgetAction, ButtonWidget, FreeWidget, Label, 
                                FunctionGui, Image, Table)
                _obj = obj
                if (not isinstance(obj.widget, _hide_labels)) and self.labels:
                    _obj = _LabeledWidgetAction.from_action(obj)
                _obj.parent = self
                insert_action_like(self.native, key, _obj.native)
                
            self._list.insert(key, obj)
        else:
            raise TypeError(f"{type(obj)} is not supported.")
    
    
    def insert(self, key: int, obj: Callable | MenuGuiBase | AbstractAction) -> None:
        """
        Insert object into the menu. Could be widget or callable.

        Parameters
        ----------
        key : int
            Position to insert.
        obj : Callable | MenuGuiBase | AbstractAction | Widget
            Object to insert.
        """
        self._fast_insert(key, obj)
        self._unify_label_widths()
        
    
def insert_action_like(qmenu: QMenu, key: int, obj):
    """
    Insert a QObject into a QMenu in a Pythonic way, like qmenu.insert(key, obj).

    Parameters
    ----------
    qmenu : QMenu
        QMenu object to which object will be inserted.
    key : int
        Position to insert.
    obj : QMenu or QAction or "sep"
        Object to be inserted.
    """    
    actions = qmenu.actions()
    l = len(actions)
    if key < 0:
        key = key + l
    if key == l:
        if isinstance(obj, QMenu):
            qmenu.addMenu(obj)
        elif obj == "sep":
            qmenu.addSeparator()
        else:
            qmenu.addAction(obj)
    else:
        new_action = actions[key]
        before = new_action
        if isinstance(obj, QMenu):
            qmenu.insertMenu(before, obj)
        elif obj == "sep":
            qmenu.insertSeparator(before)
        else:
            qmenu.insertAction(before, obj)
        
    
class MenuGui(MenuGuiBase):
    """Magic class that will be converted into a menu bar."""

class ContextMenuGui(MenuGuiBase):
    """Magic class that will be converted into a context menu."""
    # TODO: Prevent more than one context menu
