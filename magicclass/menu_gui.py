from __future__ import annotations
from typing import Callable
import warnings
from magicgui.widgets import Container
from magicgui.widgets._bases import ButtonWidget
from qtpy.QtWidgets import QMenu

from .fields import MagicField
from .widgets import Separator
from .mgui_ext import Action
from ._base import BaseGui, PopUpMode, ErrorMode
from .macro import Expr, Head, Symbol, symbol
from .utils import iter_members, define_callback, InvalidMagicClassError

class MenuGuiBase(BaseGui):
    _component_class = Action
    
    def __init__(self, 
                 parent=None, 
                 name: str = None,
                 close_on_run: bool = None,
                 popup_mode: str|PopUpMode = None,
                 error_mode: str|ErrorMode = None
                 ):
        if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first):
            msg = f"magicmenu does not support popup mode {popup_mode.value}."\
                   "PopUpMode.popup is used instead"
            warnings.warn(msg, UserWarning)
        elif popup_mode == PopUpMode.last:
            msg = f"magicmenu does not support popup mode {popup_mode.value}."\
                   "PopUpMode.parentlast is used instead"
            warnings.warn(msg, UserWarning)
            popup_mode = PopUpMode.parentlast
            
        super().__init__(close_on_run=close_on_run, popup_mode=popup_mode, error_mode=error_mode)
        name = name or self.__class__.__name__
        self.native = QMenu(name, parent)
        self.native.setToolTipsVisible(True)
        self.native.setObjectName(self.__class__.__name__)
        self._list: list[MenuGuiBase|Action] = []
        
    @property
    def parent(self):
        return self.native.parent()

    def _create_widget_from_field(self, name: str, fld: MagicField):
        cls = self.__class__
        if fld.not_ready():
            try:
                fld.default_factory = cls.__annotations__[name]
                if isinstance(fld.default_factory, str):
                    # Sometimes annotation is not type but str. 
                    from pydoc import locate
                    fld.default_factory = locate(fld.default_factory)
                    
            except (AttributeError, KeyError):
                pass
            
        fld.name = fld.name or name.replace("_", " ")
        widget = fld.to_widget()
            
        if isinstance(widget, ButtonWidget):
            # If the field has callbacks, connect it to the newly generated widget.
            widget = Action(checkable=True, checked=widget.value, text=widget.name, name=widget.name)
            for callback in fld.callbacks:
                # funcname = callback.__name__
                widget.changed.connect(define_callback(self, callback))
                     
            # By default, set value function will be connected to the widget.
            if fld.record:
                widget.changed.connect(_value_widget_callback(self, widget, name))
                
        return widget
    
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
                    # Nested magic-menu
                    widget = attr()
                    setattr(self, name, widget)
                
                elif isinstance(attr, MagicField):
                    widget = self._create_widget_from_field(name, attr)
                    
                else:
                    # convert class method into instance method
                    if not hasattr(attr, "__magicclass_wrapped__"):
                        widget = getattr(self, name, None)
                    else:
                        # If the method is redefined, the newer one should be used instead, while the
                        # order of widgets should be follow the place of the older method.
                        widget = attr.__magicclass_wrapped__.__get__(self)
                
                if name.startswith("_"):
                    continue
                if callable(widget) or isinstance(widget, (MenuGuiBase, Action, Separator, Container)):
                    self.append(widget)
                    _hist.append((name, str(type(attr)), type(widget).__name__))
            
            except Exception as e:
                hist_str = "\n\t".join(map(
                    lambda x: f"{x[0]} {x[1]} -> {x[2]}",
                    _hist
                    )) + f"\n\t\t{name} ({type(attr).__name__}) <--- Error"
                if not hist_str.startswith("\n\t"):
                    hist_str += "\n\t"
                if isinstance(e, InvalidMagicClassError):
                    e.args = (f"\n{hist_str}\n{e}",)
                    raise e
                else:
                    raise InvalidMagicClassError(f"{hist_str}\n\n{type(e).__name__}: {e}")
        
        return None
    
    def __getitem__(self, key):
        out = None
        for obj in self._list:
            if obj.name == key:
                out = obj
                break
        if out is None:
            raise KeyError(key)
        return out
    
    def append(self, obj: Callable | MenuGuiBase | Action | Separator | Container):
        if isinstance(obj, self._component_class):
            self.native.addAction(obj.native)
            self._list.append(obj)
        elif callable(obj):
            action = self._create_widget_from_method(obj)
            self.append(action)
        elif isinstance(obj, MenuGuiBase):
            obj.__magicclass_parent__ = self
            self.native.addMenu(obj.native)
            obj.native.setParent(self.native, obj.native.windowFlags())
            self._list.append(obj)
        elif isinstance(obj, Separator):
            self.native.addSeparator()
        elif isinstance(obj, Container):
            obj.__magicclass_parent__ = self
            obj.native.setParent(self.native, obj.native.windowFlags())
            _func = lambda: obj.show()
            _func.__name__ = obj.name
            action = self._create_widget_from_method(_func)
            self.append(action)
        else:
            raise TypeError(f"{type(obj)} is not supported.")

class MenuGui(MenuGuiBase):
    """Magic class that will be converted into a menu bar."""

class ContextMenuGui(MenuGuiBase):
    """Magic class that will be converted into a context menu."""
    # TODO: Prevent more than one context menu

def _value_widget_callback(mgui: MenuGuiBase, widget: ButtonWidget, name: str, getvalue: bool = True):
    def _set_value():
        if not widget.enabled:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None
        
        if isinstance(widget.value, Exception):
            return None
        
        mgui.changed.emit(mgui)
        
        if getvalue:
            sub = Expr(head=Head.getattr, args=[Symbol(name), Symbol("value")]) # name.value
        else:
            sub = Expr(head=Head.value, args=[Symbol(name)])
        
        # Make an expression of
        # >>> x.name.value = value
        # or
        # >>> x.name = value
        expr = Expr(head=Head.assign, 
                    args=[Expr(head=Head.getattr, 
                               args=[symbol(mgui), sub]), 
                          widget.value])
        
        last_expr = mgui._recorded_macro[-1]
        if (last_expr.head == expr.head and 
            last_expr.args[0].args[1].head == expr.args[0].args[1].head and
            last_expr.args[0].args[1].args[0] == expr.args[0].args[1].args[0]):
            mgui._recorded_macro[-1] = expr
        else:
            mgui._recorded_macro.append(expr)
        return None
    return _set_value