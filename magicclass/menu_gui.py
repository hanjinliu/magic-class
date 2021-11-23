from __future__ import annotations
from typing import Callable, Iterable
import warnings
from inspect import signature
from magicgui.events import Signal
from magicgui.widgets import Container, Image, Table, Label, FunctionGui
from magicgui.application import use_app
from magicgui.widgets._bases import ButtonWidget
from magicgui.widgets._bases.widget import Widget
from qtpy.QtWidgets import QMenu

from .fields import MagicField
from .widgets import Separator, FreeWidget
from .mgui_ext import AbstractAction, Action, WidgetAction, _LabeledWidgetAction
from ._base import BaseGui, PopUpMode, ErrorMode
from .macro import Expr, Head, Symbol, symbol
from .utils import get_parameters, iter_members, define_callback, InvalidMagicClassError

class MenuGuiBase(BaseGui):
    _component_class = Action
    changed = Signal(object)
    
    def __init__(self, 
                 parent=None, 
                 name: str = None,
                 close_on_run: bool = None,
                 popup_mode: str|PopUpMode = None,
                 error_mode: str|ErrorMode = None,
                 labels: bool = True
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
        self._list: list[MenuGuiBase | AbstractAction] = []
        self.labels = labels
        
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
        action = fld.get_action(self)
            
        if action.support_value:
            # If the field has callbacks, connect it to the newly generated widget.
            for callback in fld.callbacks:
                # funcname = callback.__name__
                action.changed.connect(define_callback(self, callback))
                     
            # By default, set value function will be connected to the widget.
            if fld.record:
                f = _value_widget_callback(self, action, name, getvalue=type(fld) is MagicField)
                action.changed.connect(f)
                
        return action
    
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
                elif isinstance(widget, Widget):
                    if isinstance(attr, FunctionGui):
                        widget = attr
                        p0 = list(signature(attr).parameters)[0]
                        getattr(widget, p0).bind(self) # set self to the first argument
                        # magic-class has to know when the nested FunctionGui is called.
                        f = _nested_function_gui_callback(self, widget)
                        widget.called.connect(f)
                    
                    if not isinstance(attr, Separator):
                        waction = WidgetAction(widget, name=name, parent=self.native)
                        widget = waction
                    
                if isinstance(widget, (MenuGuiBase, AbstractAction, Separator, Container, Callable)):
                    if (not isinstance(widget, Widget)) and callable(widget):
                        widget = self._create_widget_from_method(widget)
                                            
                    self.append(widget)
                    _hist.append((name, str(type(attr)), type(widget).__name__))
            
            except Exception as e:
                hist_str = "\n\t".join(map(
                    lambda x: f"{x[0]} {x[1]} -> {x[2]}",
                    _hist
                    )) + f"\n\t\t{name} ({type(attr).__name__}) <--- Error"
                if not hist_str.startswith("\n\t"):
                    hist_str = "\n\t" + hist_str
                if isinstance(e, InvalidMagicClassError):
                    e.args = (f"\n{hist_str}\n{e}",)
                    raise e
                else:
                    raise InvalidMagicClassError(f"{hist_str}\n\n{type(e).__name__}: {e}")
        
        return None
    
    def __getitem__(self, key: int|str) -> MenuGuiBase | AbstractAction:
        if isinstance(key, int):
            return self._list[key]
        
        out = None
        for obj in self._list:
            if obj.name == key:
                out = obj
                break
        if out is None:
            raise KeyError(key)
        return out
    
    def __iter__(self) -> Iterable[MenuGuiBase | AbstractAction]:
        return iter(self._list)
    
    def append(self, obj: Callable | MenuGuiBase | AbstractAction | Separator | Container):
        if isinstance(obj, self._component_class):
            self.native.addAction(obj.native)
            self._list.append(obj)
        elif isinstance(obj, Separator):
            self.native.addSeparator()
        elif isinstance(obj, WidgetAction):
            _hide_labels = (_LabeledWidgetAction, ButtonWidget, FreeWidget, Label, FunctionGui,
                            Image, Table)
            _obj = obj
            if not isinstance(obj.widget, _hide_labels):
                _obj = _LabeledWidgetAction.from_action(obj)
            _obj.parent = self
            self.native.addAction(_obj.native)
            self._list.append(obj)
            self._unify_label_widths()
        elif isinstance(obj, MenuGuiBase):
            obj.__magicclass_parent__ = self
            self.native.addMenu(obj.native)
            obj.native.setParent(self.native, obj.native.windowFlags())
            self._list.append(obj)
        elif isinstance(obj, Container):
            obj.__magicclass_parent__ = self
            obj.native.setParent(self.native, obj.native.windowFlags())
            _func = lambda: obj.show()
            _func.__name__ = obj.name
            action = self._create_widget_from_method(_func)
            self.append(action)
        else:
            raise TypeError(f"{type(obj)} is not supported.")
    
    def _unify_label_widths(self):
        _hide_labels = (_LabeledWidgetAction, ButtonWidget, FreeWidget, Label, FunctionGui,
                        Image, Table, Action)
        need_labels = [w for w in self if not isinstance(w, _hide_labels)]
        
        if self.labels and need_labels:
            measure = use_app().get_obj("get_text_width")
            widest_label = max(measure(w.label) for w in need_labels)
            for w in need_labels:
                labeled_widget = w._labeled_widget()
                if labeled_widget:
                    labeled_widget.label_width = widest_label

class MenuGui(MenuGuiBase):
    """Magic class that will be converted into a menu bar."""

class ContextMenuGui(MenuGuiBase):
    """Magic class that will be converted into a context menu."""
    # TODO: Prevent more than one context menu

def _nested_function_gui_callback(menugui: MenuGuiBase, fgui: FunctionGui):
    def _after_run():
        inputs = get_parameters(fgui)
        args = [Expr(head=Head.kw, args=[Symbol(k), v]) for k, v in inputs.items()]
        # args[0] is self
        sub = Expr(head=Head.getattr, args=[menugui._recorded_macro[0].args[0], Symbol(fgui.name)]) # {x}.func
        expr = Expr(head=Head.call, args=[sub] + args[1:]) # {x}.func(args...)

        if fgui._auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last input
            # will be recorded in magic-class.
            last_expr = menugui._recorded_macro[-1]
            if last_expr.head == Head.call and last_expr.args[0].head == Head.getattr and \
                last_expr.args[0].args[1] == expr.args[0].args[1]:
                menugui._recorded_macro.pop()

        menugui._recorded_macro.append(expr)
    return _after_run

def _value_widget_callback(menugui: MenuGuiBase, action: AbstractAction, name: str, getvalue: bool = True):
    def _set_value():
        if not action.enabled:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None
        
        if isinstance(action.value, Exception):
            return None
        
        menugui.changed.emit(menugui)
        
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
                               args=[symbol(menugui), sub]), 
                          action.value])
        
        last_expr = menugui._recorded_macro[-1]
        if (last_expr.head == expr.head and 
            last_expr.args[0].args[1].head == expr.args[0].args[1].head and
            last_expr.args[0].args[1].args[0] == expr.args[0].args[1].args[0]):
            menugui._recorded_macro[-1] = expr
        else:
            menugui._recorded_macro.append(expr)
        return None
    return _set_value