from __future__ import annotations
from functools import wraps
from typing import Callable, Any
import inspect
import numpy as np
from docstring_parser import parse
from magicgui import magicgui
from qtpy.QtWidgets import QMenu, QAction
import napari
from .utils import iter_members, n_parameters
from .macro import Macro, Expr, Head, MacroMixin
from .wrappers import upgrade_signature

from .utils import (iter_members, n_parameters, extract_tooltip, raise_error_in_msgbox, 
                    raise_error_msg, find_unique_name)


class MenuGui(MacroMixin):
    def __init__(self, parent=None, name=None):
        super().__init__()
        name = name or self.__class__.__name__
        self.native = QMenu(name, parent)
        self._actions = []
        self.__magicclass_parent__: None = None
        self._parameter_history: dict[str, dict[str, Any]] = {}
        self._recorded_macro: Macro[Expr] = Macro()
        self.native.setObjectName(self.__class__.__name__)
        
        self.label = None
    
    @property
    def parent(self):
        return self.native.parent()
    
    @property
    def parent_viewer(self) -> "napari.Viewer"|None:
        """
        Return napari.Viewer if self is a dock widget of a viewer.
        """        
        try:
            viewer = self.parent.qt_viewer.viewer
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
            
            else:
                # convert class method into instance method
                widget = getattr(self, name, None)
                            
            if not name.startswith("_") and (callable(widget) or isinstance(widget, MenuGui)):
                self.append(widget)
        
        return None
    
    def append(self, obj: Callable|MenuGui):
        if callable(obj):
            action = self._convert_method_into_action(obj)
            self.native.addAction(action)
            self._actions.append(action)
        elif isinstance(obj, MenuGui):
            self.native.addMenu(obj.native)
            self._actions.append(obj.native)
        else:
            raise TypeError(type(obj))
        
    # def insert(self, key: int, obj):
    #     before = self._actions[key]
    #     if callable(obj):
    #         action = QAction(obj.__name__, self.native)
    #         action.triggered.connect(obj)
    #         self.native.insertAction(before, action)
    #     elif isinstance(obj, self.__class__):
    #         self.native.insertMenu(before, obj)
    #     else:
    #         raise TypeError(type(obj))
    
    @classmethod
    def wraps(cls, method:Callable) -> Callable:
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
    
    def _convert_method_into_action(self, obj):
        # Convert methods into push buttons
        text = obj.__name__.replace("_", " ")
        action = QAction(text, self.native)

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
            def run_function(*args):
                return func()
        else:
            def run_function(*args):
                # if action.mgui is not None:
                #     action.mgui.native.activateWindow()
                #     return None
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
                
                # if self.parent:
                #     mgui.native.setParent(self.parent)
                    
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
                
                # f = _temporal_function_gui_callback(self, mgui, button)
                # mgui.called.connect(f)
                # action.mgui = mgui
                return None
            
        action.triggered.connect(run_function)
        
        # If button design is given, load the options.
        # action.from_options(obj)
            
        return action


# from magicgui.backends._qtpy import QBaseValueWidget

# class Action(QBaseValueWidget):
#     def __init__(self):
#         super().__init__(
#             self, QAction, "triggered"
#         )