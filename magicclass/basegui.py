from __future__ import annotations
from functools import wraps
from typing import Callable
import inspect
import numpy as np
from magicgui import magicgui
from magicgui.widgets import Container, Label
from magicgui.widgets._bases import Widget
from .utils import iter_members
from .widgets import PushButtonPlus, Separator, Logger, raise_error_msg

# Check if napari is available so that layers are detectable from GUIs.
try:
    import napari
except ImportError:
    NAPARI_AVAILABLE = False
else:
    NAPARI_AVAILABLE = True
    
LOGGER = Logger(name="logger")


# TODO: 
# - progress bar
# - some responses when function call finished, like "idle" and "busy"
# - think of nesting magic-class
# - GUI tester
# - "exclusive" mode


class BaseGui(Container):
    error_handling = "messagebox"
    
    def __init__(self, layout:str= "vertical", close_on_run:bool=True, popup:bool=True, name=None):
        super().__init__(layout=layout, labels=False, name=name)
        self._current_dock_widget = None
        self._close_on_run = close_on_run
        self._popup = popup
        self._parameter_history:dict[str, dict[str]] = {}
        self.native.setObjectName(self.__class__.__name__)
    
    @property
    def parent_viewer(self) -> "napari.Viewer"|None:
        """
        Return napari.Viewer if self is a dock widget of a viewer.
        """        
        try:
            viewer = self.parent.parent().qt_viewer.viewer
        except AttributeError:
            viewer = None
        return viewer
    
    def _convert_methods_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            doc = cls.__doc__.strip()
            lbl = Label(value=doc)
            self.append(lbl)
        
        # Bind all the methods
        base_members = set(iter_members(BaseGui))
        for name in filter(lambda x: x not in base_members, iter_members(cls)):
            func = getattr(self, name, None)
            if callable(func):
                self.append(func)
        
        return self
    
    def append(self, obj:Widget|Callable) -> None:
        """
        This override enables methods/functions to be appended into Container widgets.
        """        
        if (not isinstance(obj, Widget)) and callable(obj):
            name = obj.__name__.replace("_", " ")
            button = PushButtonPlus(name=obj.__name__, text=name)

            # Wrap function to deal with errors in a right way.
            wrapper = {"messagebox": _wrap_with_msgbox,
                       "logger": _wrap_with_logger,
                       }.get(self.__class__.error_handling, _wrap_with_nothing)
            
            func = wrapper(obj, parent=self.native)
            
            # Strangely, signature must be updated like this. Otherwise, already wrapped member function
            # will have signature with "self".
            func.__signature__ = inspect.signature(obj)

            # Prepare a button
            button.tooltip = func.__doc__.strip() if func.__doc__ else ""
            
            if len(inspect.signature(func).parameters) == 0:
                # We don't want a dialog with a single widget "Run" to show up.
                def run_function(*args):
                    return func()
            else:
                def run_function(*args):
                    func_obj_name = f"function-{id(func)}"
                    try:
                        mgui = magicgui(func)
                        mgui.name = func_obj_name
                            
                    except Exception as e:
                        msg = f"Exception was raised during building magicgui.\n{e.__class__.__name__}: {e}"
                        raise_error_msg(self.native, msg=msg)
                        return None
                    
                    # Recover last inputs if exists.
                    params = self._parameter_history.get(func.__name__, {})
                    for key, value in params.items():
                        try:
                            getattr(mgui, key).value = value
                        except ValueError:
                            pass
                    
                    viewer = self.parent_viewer
                    
                    # TODO: use FunctionGui.close and FunctionGui.called.connect in new version of magicgui
                    
                    if viewer is None:
                        # If napari.Viewer was not found, then open up a magicgui when button is pushed, and 
                        # close it when function call is finished (if close_on_run==True).
                        if self._popup:
                            mgui.show()
                        else:
                            sep = Separator(orientation="horizontal", text=name)
                            mgui.insert(0, sep)
                            self.append(mgui)
                            
                        if self._close_on_run:
                            @mgui._call_button.changed.connect
                            def _close_widget(*args):
                                inputs = _record_parameter(mgui)
                                self._parameter_history.update({func.__name__: inputs})
                                if not self._popup:
                                    self.remove(func_obj_name)
                                mgui.native.close()
                    else:
                        # If napari.Viewer was found, then create a magicgui as a dock widget when button is 
                        # pushed, and remove it when function call is finished (if close_on_run==True).
                        viewer: napari.Viewer
                        if self._close_on_run:
                            def _close_widget(*args):
                                inputs = _record_parameter(mgui)
                                self._parameter_history.update({func.__name__: inputs})
                                viewer.window.remove_dock_widget(mgui.parent)
                                mgui.native.close()
                                
                            _prepend_callback(mgui._call_button, _close_widget)
                        
                        dock_name = _find_unique_name(name, viewer)
                        dock = viewer.window.add_dock_widget(mgui, name=dock_name)
                        mgui.native.setParent(dock)
                        dock.setFloating(self._popup)
                        
                    return None
                
            button.changed.connect(run_function)
            try:
                options = obj.__signature__.caller_options
            except AttributeError:
                pass
            else:
                button.from_options(options)
                
            obj = button
            
        super().append(obj)
        return None
    
    def objectName(self):
        """
        This function makes the object name discoverable by napari's `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()
    
    def show(self):
        super().show()
        self.native.activateWindow()
        return None
    

def _wrap_with_msgbox(func, parent=None):
    """
    Wrapper for error handling during GUI running. Instead of raising error in console, show a message box.
    """    
    # TODO: Should be wrapped in notification manager if the widget is dockec in napari.
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            raise_error_msg(parent, title=e.__class__.__name__, msg=str(e))
            out = None
        finally:
            pass
        return out
    
    return wrapped_func

def _wrap_with_logger(func, parent=None): # WIP
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            log = [f'{func.__name__}: <span style="color: red; font-weight: bold;">{e.__class__.__name__}</span>',
                   f'{e}']
            
            out = None
        else:
            log = f'{func.__name__}: <span style="color: blue; font-weight: bold;">Pass</span>'
        LOGGER.append(log)
        LOGGER.visible or LOGGER.show()
        return out
    
    return wrapped_func

def _wrap_with_nothing(func, parent=None):
    return func

def _find_unique_name(name:str, viewer:"napari.Viewer"):
    orig_name = name
    i = 0
    while name in viewer.window._dock_widgets:
        name = orig_name + f"-{i}"
        i += 1
    return name

def _record_parameter(mgui):
    inputs = {param: getattr(mgui, param).value
              for param, value in mgui.__signature__.parameters.items()
              if not isinstance(value, np.ndarray)   # TODO: this filter is not a good way
              }
    
    return inputs

def _prepend_callback(call_button: PushButtonPlus, callback):
    old_callbacks = call_button.changed.callbacks
    call_button.changed.disconnect()
    new_callbacks = (callback,) + old_callbacks
    for c in new_callbacks:
        call_button.changed.connect(c)
    return call_button