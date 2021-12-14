from __future__ import annotations
from typing import Callable
import warnings
from inspect import signature
from magicgui.widgets import Image, Table, Label, FunctionGui
from magicgui.widgets._bases import ButtonWidget
from magicgui.widgets._bases.widget import Widget
from macrokit import Symbol
from qtpy.QtWidgets import QToolBar

from .mgui_ext import AbstractAction, _LabeledWidgetAction, WidgetAction, ToolButtonPlus
from ._base import BaseGui, PopUpMode, ErrorMode, ContainerLikeGui, nested_function_gui_callback
from .utils import MagicClassConstructionError
from .menu_gui import MenuGuiBase, insert_action_like

from ..signature import get_additional_option
from ..fields import MagicField
from ..widgets import FreeWidget, Separator
from ..utils import iter_members


def _check_popupmode(popup_mode: PopUpMode):
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first):
        msg = f"magictoolbar does not support popup mode {popup_mode.value}."\
                "PopUpMode.popup is used instead"
        warnings.warn(msg, UserWarning)
    elif popup_mode == PopUpMode.last:
        msg = f"magictoolbat does not support popup mode {popup_mode.value}."\
                "PopUpMode.parentlast is used instead"
        warnings.warn(msg, UserWarning)
        popup_mode = PopUpMode.parentlast
    
    return popup_mode


class ToolBarGui(ContainerLikeGui):
    def __init__(self, 
                 parent=None, 
                 name: str = None,
                 close_on_run: bool = None,
                 popup_mode: str | PopUpMode = None,
                 error_mode: str | ErrorMode = None,
                 labels: bool = True
                 ):
        popup_mode = _check_popupmode(popup_mode)
            
        super().__init__(close_on_run=close_on_run, popup_mode=popup_mode, error_mode=error_mode)
        name = name or self.__class__.__name__
        self.native = QToolBar(name, parent)
        self.name = name
        self._list: list[MenuGuiBase | AbstractAction] = []
        self.labels = labels
    
    
    def _convert_attributes_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)
            
        # Bind all the methods and annotations
        base_members = set(x[0] for x in iter_members(ToolBarGui))        
        
        _hist: list[tuple[str, str, str]] = [] # for traceback
        
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            try:
                if isinstance(attr, type):
                    # Nested magic-menu
                    widget = attr()
                    setattr(self, name, widget)
                
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
                    # magic-class has to know when the nested FunctionGui is called.
                    f = nested_function_gui_callback(self, widget)
                    widget.called.connect(f)
                
                elif isinstance(widget, MenuGuiBase): # TODO: contextmenu?
                    tb = ToolButtonPlus(widget.name)
                    tb.set_menu(widget.native)
                    tb.tooltip = widget.__doc__
                    widget.__magicclass_parent__ = self
                    widget._my_symbol = Symbol(name)
                    widget = WidgetAction(tb, tb.name)
                
                elif isinstance(widget, ToolBarGui):
                    raise NotImplementedError("nested Toolbar is not implemented yet.")
                
                elif isinstance(widget, Separator):
                    pass
                
                elif isinstance(widget, Widget):
                    widget = WidgetAction(widget, widget.name)
                    
                if isinstance(widget, (AbstractAction, Callable)):
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
                        self.append(widget)
                    
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
        
        return None
    
    
    def insert(self, key: int, obj: AbstractAction) -> None:
        """
        Insert object into the menu. Could be widget or callable.

        Parameters
        ----------
        key : int
            Position to insert.
        obj : Callable | MenuGuiBase | AbstractAction | Widget
            Object to insert.
        """        
        # _hide_labels should not contain Container because some ValueWidget like widgets
        # are Containers.
        if isinstance(obj, self._component_class):
            insert_action_like(self.native, key, obj.native)
            self._list.insert(key, obj)
        elif isinstance(obj, Separator):
            insert_action_like(self.native, key, "sep")
            self._list.insert(key, obj)
        elif isinstance(obj, WidgetAction):
            if isinstance(obj.widget, Separator):
                self.insert(key, obj.widget)
            else:
                _hide_labels = (_LabeledWidgetAction, ButtonWidget, FreeWidget, Label, 
                                FunctionGui, Image, Table)
                _obj = obj
                if not isinstance(obj.widget, _hide_labels):
                    _obj = _LabeledWidgetAction.from_action(obj)
                _obj.parent = self
                insert_action_like(self.native, key, _obj.native)
                self._unify_label_widths()
                self._list.insert(key, obj)
        else:
            raise TypeError(f"{type(obj)} is not supported.")

