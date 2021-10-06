from __future__ import annotations
from functools import wraps
from typing import Callable, Any, TYPE_CHECKING
from dataclasses import MISSING
import inspect
from magicgui import magicgui
from magicgui.widgets import FunctionGui, FileEdit
from qtpy.QtWidgets import QMenu, QAction
import napari
from magicclass.field import MagicField

from magicclass.widgets import Separator
from .utils import define_callback, iter_members, n_parameters
from .macro import Macro, Expr, Head, MacroMixin
from .wrappers import upgrade_signature

from .utils import (iter_members, n_parameters, extract_tooltip, raise_error_in_msgbox, 
                    raise_error_msg, get_parameters, find_unique_name, show_mgui)

if TYPE_CHECKING:
    from .class_gui import ClassGui


class Action(QAction):
    def __init__(self, *args, name=None, text=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.mgui = None
        if text:
            self.text = text
        if name:
            self.setObjectName(name)
        self._callbacks = []
        
    @property
    def name(self) -> str:
        return self.objectName()
    
    @name.setter
    def name(self, value: str):
        self.setObjectName(value)
    
    @property
    def text(self) -> str:
        return super().text()
    
    @text.setter
    def text(self, value: str):
        self.setText(value)
    
    @property
    def enabled(self):
        return self.isEnabled()
    
    @enabled.setter
    def enabled(self, value: bool):
        self.setEnabled(value)
    
    @property
    def value(self):
        return self.isChecked()
    
    @value.setter
    def value(self, checked: bool):
        self.setChecked(checked)
    
    @property
    def visible(self):
        return self.isVisible()
    
    @visible.setter
    def visible(self, value: bool):
        self.setVisible(value)
    
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

class MenuGui(MacroMixin):
    def __init__(self, parent=None, name=None):
        super().__init__()
        name = name or self.__class__.__name__
        self.native = QMenu(name, parent)
        self._list: list[MenuGui|Action] = []
        self.__magicclass_parent__: None|ClassGui|MenuGui = None
        self._parameter_history: dict[str, dict[str, Any]] = {}
        self._recorded_macro: Macro[Expr] = Macro()
        self.native.setObjectName(self.__class__.__name__)
            
    @property
    def parent(self):
        return self.native.parent()
    
    @property
    def parent_viewer(self) -> "napari.Viewer"|None:
        """
        Return napari.Viewer if self is a dock widget of a viewer.
        """        
        current_self = self
        while hasattr(current_self, "__magicclass_parent__") and current_self.__magicclass_parent__:
            current_self = current_self.__magicclass_parent__
        
        try:
            viewer = current_self.parent.parent().qt_viewer.viewer
        except AttributeError:
            viewer = None
        return viewer
    
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
            if obj.objectName() == key:
                out = obj
                break
        if out is None:
            raise KeyError(key)
        return out
    
    def append(self, obj: Callable|MenuGui|Action|Separator):
        if isinstance(obj, Action):
            self.native.addAction(obj)
            self._list.append(obj)
        elif callable(obj):
            action = self._convert_method_into_action(obj)
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
        
    @classmethod
    def wraps(cls, method: Callable) -> Callable:
        def _childmethod(self:cls, *args, **kwargs):
            current_self = self.__magicclass_parent__
            while not (hasattr(current_self, funcname) and 
                        current_self.__class__.__name__ == clsname):
                current_self = current_self.__magicclass_parent__
            return getattr(current_self, funcname)(*args, **kwargs)
        
        clsname, funcname = method.__qualname__.split(".")
        childmethod = wraps(method)(_childmethod)
        
        # To avoid two buttons with same bound function being showed up
        upgrade_signature(method, caller_options={"visible": False})
        
        if hasattr(cls, funcname):
            # Sometimes we want to pre-define function to arrange the order of widgets.
            # By updating __wrapped__ attribute we can overwrite the line number
            childmethod.__wrapped__ = getattr(cls, funcname)
        
        if hasattr(method, "__doc__"):
            childmethod.__doc__ = method.__doc__
        setattr(cls, funcname, childmethod)
        return method
    
    def _create_widget_from_field(self, name: str, fld: MagicField):
        value = False if fld.default is MISSING else fld.default
        text = fld.metadata.get("text", name)
        action = Action(name=name, text=text, parent=None, checkable=True, checked=value)
        for callback in fld.callbacks:
            callback = define_callback(self, callback)
            action.triggered.connect(callback)
            action._callbacks.append(callback)
            
        @action.triggered.connect
        def _set_value(event):
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
    
    def _convert_method_into_action(self, obj):
        # Convert methods into push buttons
        text = obj.__name__.replace("_", " ")
        action = Action(name=obj.__name__, text=text, parent=self.native)

        # Wrap function to deal with errors in a right way.
        wrapper = raise_error_in_msgbox
        
        func = wrapper(obj, parent=self)
        
        # Signature must be updated like this. Otherwise, already wrapped member function
        # will have signature with "self".
        func.__signature__ = inspect.signature(obj)

        # Prepare a button
        action.setToolTip(extract_tooltip(func))
        
        if n_parameters(func) == 0:
            # We don't want a dialog with a single widget "Run" to show up.
            f = _temporal_function_gui_callback(self, func, action)
            def run_function(*args):
                out = func()
                f(out)
                return out
        
        elif n_parameters(func) == 1 and type(FunctionGui.from_callable(func)[0]) is FileEdit:
            f = _temporal_function_gui_callback(self, func, action)
            def run_function(*args):
                action.mgui = FunctionGui.from_callable(func)[0]
                action.mgui._on_choose_clicked()
                out = func(action.mgui.value)
                f(out)
                return out
            
        else:
            def run_function(*args):
                if action.mgui is not None:
                    show_mgui(action.mgui)
                    return None
                try:
                    mgui = magicgui(func)
                    mgui.name = f"function-{id(func)}"
                        
                except Exception as e:
                    msg = f"Exception was raised during building magicgui.\n{e.__class__.__name__}: {e}"
                    raise_error_msg(self.native, msg=msg)
                    raise e
                
                # Recover last inputs if exists.
                params = self._parameter_history.get(func.__name__, {})
                for key, value in params.items():
                    try:
                        getattr(mgui, key).value = value
                    except ValueError:
                        pass
                
                viewer = self.parent_viewer
                        
                if viewer is None:
                    mgui.show()
                    
                    @mgui.called.connect
                    def _close(value):
                        mgui.close()
                            
                else:
                    # If napari.Viewer was found, then create a magicgui as a dock widget when button is 
                    # pushed, and remove it when function call is finished (if close_on_run==True).
                    viewer: napari.Viewer
                    @mgui.called.connect
                    def _close(value):
                        viewer.window.remove_dock_widget(mgui.parent)
                        mgui.close()
                            
                    dock_name = find_unique_name(text, viewer)
                    dock = viewer.window.add_dock_widget(mgui, name=dock_name)
                    dock.setFloating(True)
                
                f = _temporal_function_gui_callback(self, mgui, action)
                mgui.called.connect(f)
                action.mgui = mgui
                return None
            
        action.triggered.connect(run_function)
        action.from_options(obj)
        return action

def _temporal_function_gui_callback(menugui:MenuGui, fgui:FunctionGui|Callable, action:Action):
    def _after_run(value):
        if isinstance(value, Exception):
            return None
        
        if isinstance(fgui, FunctionGui):
            inputs = get_parameters(fgui)
            menugui._record_parameter_history(fgui._function.__name__, inputs)
            _function = fgui._function
        else:
            inputs = {}
            _function = fgui
        
        # if action._callbacks:
        #     # TODO: use event emitter
        #     ...
        # else:
        menugui._record_macro(_function, (), inputs)
        action.mgui = None
    return _after_run