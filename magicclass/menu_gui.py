from __future__ import annotations
from typing import Callable
from magicgui.events import Signal
from magicgui.widgets._bases import ButtonWidget
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QMenu, QAction

from .field import MagicField
from .widgets import Separator
from ._base import BaseGui, PopUpMode, ErrorMode
from .macro import Expr, Head, Symbol, symbol
from .utils import iter_members, define_callback

class Action:
    """QAction encapsulated class with a similar API as magicgui Widget."""
    changed = Signal(object)
    def __init__(self, *args, name=None, text=None, gui_only=True, **kwargs):
        self.native = QAction(*args, **kwargs)
        self.mgui = None
        self._icon_path = None
        if text:
            self.text = text
        if name:
            self.native.setObjectName(name)
        self._callbacks = []
        
        self.native.triggered.connect(lambda: self.changed.emit(self.value))
        
    @property
    def name(self) -> str:
        return self.native.objectName()
    
    @name.setter
    def name(self, value: str):
        self.native.setObjectName(value)
    
    @property
    def text(self) -> str:
        return self.native.text()
    
    @text.setter
    def text(self, value: str):
        self.native.setText(value)
    
    @property
    def tooltip(self) -> str:
        return self.native.toolTip()
    
    @tooltip.setter
    def tooltip(self, value: str):
        self.native.setToolTip(value)
    
    @property
    def enabled(self):
        return self.native.isEnabled()
    
    @enabled.setter
    def enabled(self, value: bool):
        self.native.setEnabled(value)
    
    @property
    def value(self):
        return self.native.isChecked()
    
    @value.setter
    def value(self, checked: bool):
        self.native.setChecked(checked)
    
    @property
    def visible(self):
        return self.native.isVisible()
    
    @visible.setter
    def visible(self, value: bool):
        self.native.setVisible(value)
    
    @property
    def icon_path(self):
        return self._icon_path
    
    @icon_path.setter
    def icon_path(self, path:str):
        icon = QIcon(path)
        self.native.setIcon(icon)
    
    def from_options(self, options: dict[str]|Callable):
        if callable(options):
            try:
                options = options.__signature__.caller_options
            except AttributeError:
                return None
                
        for k, v in options.items():
            v = options.get(k, None)
            if v is not None:
                setattr(self, k, v)
        return None


class MenuGuiBase(BaseGui):
    _component_class = Action
    
    def __init__(self, 
                 parent=None, 
                 name: str = None,
                 close_on_run: bool = None,
                 popup_mode: str|PopUpMode = None,
                 error_mode: str|ErrorMode = None
                 ):
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
            
        widget = fld.to_widget()
        widget.name = widget.name or name
            
        if isinstance(widget, ButtonWidget):
            # If the field has callbacks, connect it to the newly generated widget.
            widget = Action(checkable=True, checked=widget.value, text=widget.name, name=widget.name)
            for callback in fld.callbacks:
                # funcname = callback.__name__
                widget.changed.connect(define_callback(self, callback))
                     
            # By default, set value function will be connected to the widget.
            widget.changed.connect(_value_widget_callback(self, widget, name))
                
        setattr(self, name, widget)
        return widget
    
    def _convert_attributes_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)
            
        # Bind all the methods and annotations
        base_members = set(x[0] for x in iter_members(MenuGuiBase))        
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
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
            if callable(widget) or isinstance(widget, (MenuGuiBase, Action, Separator)):
                self.append(widget)
        
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
    
    def append(self, obj: Callable|MenuGuiBase|Action|Separator):
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
        else:
            raise TypeError(f"{type(obj)} is not supported.")

class MenuGui(MenuGuiBase):
    """Magic class that will be converted into a menu bar."""

class ContextMenuGui(MenuGuiBase):
    """Magic class that will be converted into a context menu."""
    # TODO: Prevent more than one context menu

def _value_widget_callback(mgui: MenuGuiBase, widget: ButtonWidget, name: str):
    def _set_value():
        if not widget.enabled:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None
        value = widget.value
        if isinstance(value, Exception):
            return None
        sub = Expr(head=Head.getattr, args=[Symbol(name), Symbol("value")]) # name.value
        expr = Expr(head=Head.setattr, args=[symbol(mgui), sub, value]) # {x}.name.value = value
        
        last_expr = mgui._recorded_macro[-1]
        if last_expr.head == expr.head and last_expr.args[1].args[0] == expr.args[1].args[0]:
            mgui._recorded_macro[-1] = expr
        else:
            mgui._recorded_macro.append(expr)
    return _set_value