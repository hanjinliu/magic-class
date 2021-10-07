from __future__ import annotations
from typing import Callable
from dataclasses import MISSING
from magicgui.events import EventEmitter
from qtpy.QtWidgets import QMenu, QAction
from magicclass.field import MagicField

from magicclass.widgets import Separator
from ._base import BaseGui
from .macro import Expr, Head

from .utils import define_callback, iter_members

class Action:
    def __init__(self, *args, name=None, text=None, gui_only=True, **kwargs):
        self.native = QAction(*args, **kwargs)
        self.mgui = None
        if text:
            self.text = text
        if name:
            self.native.setObjectName(name)
        self._callbacks = []
        self.changed = EventEmitter(source=self, type="changed")
        self.native.triggered.connect(lambda e: self.changed(value=self.value))
        
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
    
    def from_options(self, options:dict[str]|Callable):
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

class MenuGui(BaseGui):
    _component_class = Action
    
    def __init__(self, 
                 parent=None, 
                 name: str = None,
                 close_on_run: bool = True,
                 popup: bool = True,
                 single_call: bool = True):
        super().__init__(close_on_run=close_on_run, popup=popup, single_call=single_call)
        name = name or self.__class__.__name__
        self.native = QMenu(name, parent)
        self._list: list[MenuGui|Action] = []
        self.native.setObjectName(self.__class__.__name__)
        
    @property
    def parent(self):
        return self.native.parent()
    
    def _convert_attributes_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)
            
        # Bind all the methods and annotations
        base_members = set(x[0] for x in iter_members(MenuGui))        
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if isinstance(attr, type):
                # Nested magic-menu
                widget = attr()
                setattr(self, name, widget)
            
            elif isinstance(attr, MagicField):
                widget = self._create_widget_from_field(name, attr)
                
            else:
                # convert class method into instance method
                widget = getattr(self, name, None)
                            
            if not name.startswith("_") and (callable(widget) or isinstance(widget, (MenuGui, Action, Separator))):
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
    
    def append(self, obj: Callable|MenuGui|Action|Separator):
        if isinstance(obj, self._component_class):
            self.native.addAction(obj.native)
            self._list.append(obj)
        elif callable(obj):
            action = self._create_widget_from_method(obj)
            self.append(action)
        elif isinstance(obj, MenuGui):
            obj.__magicclass_parent__ = self
            self.native.addMenu(obj.native)
            obj.native.setParent(self.native, obj.native.windowFlags())
            self._list.append(obj)
        elif isinstance(obj, Separator):
            self.native.addSeparator()
        else:
            raise TypeError(type(obj))
        
    def _create_widget_from_field(self, name: str, fld: MagicField):
        value = False if fld.default is MISSING else fld.default
        text = fld.metadata.get("text", name)
        action = self._component_class(name=name, text=text, parent=None, 
                                       checkable=True, checked=value)
        for callback in fld.callbacks:
            callback = define_callback(self, callback)
            action.changed.connect(callback)
            action._callbacks.append(callback)
            
        @action.changed.connect
        def _set_value(event):
            if not event.source.enabled:
                # If widget is read only, it means that value is set in script (not manually).
                # Thus this event should not be recorded as a macro.
                return None
                    
            sub = Expr(head=Head.getattr, args=[name, "value"]) # name.value
            expr = Expr(head=Head.setattr, args=["{x}", sub, value]) # {x}.name.value = value
            
            last_expr = self._recorded_macro[-1]
            if last_expr.head == expr.head and last_expr.args[1].args[0] == expr.args[1].args[0]:
                self._recorded_macro[-1] = expr
            else:
                self._recorded_macro.append(expr)
            return None
        setattr(self, name, action)
        return action
    