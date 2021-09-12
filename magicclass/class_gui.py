from __future__ import annotations
from functools import wraps
from typing import Callable, Any
import inspect
from contextlib import contextmanager
import numpy as np
from pathlib import Path
from magicgui import magicgui
from magicgui.widgets import Container, Label, LineEdit
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
    
_HARD_TO_RECORD = (np.ndarray,) # This is a temporal solution to avoid recording layer as an numpy
_INSTANCE = "ins"

# Running mode determines how to construct magic-class GUI.
# - "default": Error will be raised in message box
# - "debug": Whether function call ended with error will be recorded in a logger widget.
# - "raw": Raise errors in console (non-wrapped mode)
RUNNING_MODE = "default"

LOGGER = Logger(name="logger")

@contextmanager
def debug():
    """
    Magic-classes that are constructed within this context will enter debug mode.
    """    
    global RUNNING_MODE
    current_mode = RUNNING_MODE
    RUNNING_MODE = "debug"
    LOGGER.show()
    yield
    RUNNING_MODE = current_mode

# ideas:
# - progress bar
# - GUI tester
# - "exclusive" mode


class ClassGui(Container):
    def __init__(self, layout:str= "vertical", close_on_run:bool=True, popup:bool=True, 
                 result_widget:bool=False, name=None):
        super().__init__(layout=layout, labels=False, name=name)
        self._current_dock_widget = None
        self._close_on_run = close_on_run
        self._popup = popup
        
        self._result_widget: LineEdit | None = None
        if result_widget:
            self._result_widget = LineEdit(gui_only=True, name="result")
            
        self._parameter_history:dict[str, dict[str, Any]] = {}
        self._recorded_macro = Macro()
        self.native.setObjectName(self.__class__.__name__)
        if RUNNING_MODE == "debug":
            if LOGGER.n_line > 0:
                LOGGER.append("<hr></hr>")
            LOGGER.append(f"{self.__class__.__name__} object at {id(self)}")
    
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
    
    def _convert_methods_into_widgets(self) -> ClassGui:
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            doc = cls.__doc__.strip()
            lbl = Label(value=doc)
            self.append(lbl)
        
        # Bind all the methods
        base_members = set(iter_members(ClassGui))
        for name in filter(lambda x: x not in base_members, iter_members(cls)):
            attr = getattr(self, name, None)
            if callable(attr) or isinstance(attr, type):
                self.append(attr)
        
        # Append result widget in the bottom
        if self._result_widget is not None:
            self._result_widget.enabled = False
            self.append(self._result_widget)
        return self
    
    def _record_macro(self, func:str, args:tuple, kwargs:dict[str, Any]) -> None:
        """
        Record a function call as a line of macro.

        Parameters
        ----------
        func : str
            Name of function.
        args : tuple
            Arguments.
        kwargs : dict[str, Any]
            Keyword arguments.
        """        
        # if magic-class is nested, this function does not work.
        arg_inputs = []
        for a in args:
            if isinstance(a, _HARD_TO_RECORD):
                arg_inputs.append(f"var{id(a)}")
            elif isinstance(a, Path):
                arg_inputs.append(f"r'{a}'")
            else:
                arg_inputs.append(f"{repr(a)}")
                
        kwarg_inputs = []
        for k, v in kwargs.items():
            if isinstance(v, _HARD_TO_RECORD):
                kwarg_inputs.append(f"{k}=var{id(v)}")
            elif isinstance(v, Path):
                kwarg_inputs.append(f"{k}=r'{v}'")
            else:
                kwarg_inputs.append(f"{k}={repr(v)}")
        kwarg_inputs = ", ".join(kwarg_inputs)
        
        if func == self.__class__.__name__:
            line = f"{_INSTANCE} = {func}({kwarg_inputs})"
        else:
            line = f"{_INSTANCE}.{func}({kwarg_inputs})"
        self._recorded_macro.append(line)
        return None
    
    def _record_parameter_history(self, func:str, kwargs:dict[str, Any]) -> None:
        """
        Record parameter inputs to history for next call.

        Parameters
        ----------
        func : str
            Name of function.
        kwargs : dict[str, Any]
            Parameter inputs.
        """        
        kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, _HARD_TO_RECORD)}
        self._parameter_history.update({func: kwargs})
        return None
    
    def append(self, obj:Widget|Callable|type) -> None:
        """
        This override enables methods/functions and other magic-class to be appended into Container 
        widgets. Compatible with ``@magicgui`` and ``@magicclass`` decorators inside class. If 
        ``FunctionGui`` object or ``ClassGui`` object was appended, it will appear on the container as is, rather than a push button.
        """        
        if isinstance(obj, type):
            # Inline class definition
            if issubclass(obj, ClassGui):
                obj = obj()
            else:
                raise TypeError(f"Cannot append class except for ClassGui (got {obj.__name__})")
            
        elif (not isinstance(obj, Widget)) and callable(obj):
            name = obj.__name__.replace("_", " ")
            button = PushButtonPlus(name=obj.__name__, text=name, gui_only=True)

            # Wrap function to deal with errors in a right way.
            if RUNNING_MODE == "default":
                wrapper = _raise_error_in_msgbox
            elif RUNNING_MODE == "debug":
                wrapper = _write_log
            elif RUNNING_MODE == "raw":
                wrapper = lambda x, parent: x
            else:
                raise ValueError(f"RUNNING_MODE={RUNNING_MODE}")
            func = wrapper(obj, parent=self.native)
            
            # Strangely, signature must be updated like this. Otherwise, already wrapped member function
            # will have signature with "self".
            func.__signature__ = inspect.signature(obj)

            # Prepare a button
            button.tooltip = func.__doc__.strip() if func.__doc__ else ""
            
            if len(inspect.signature(func).parameters) == 0:
                # We don't want a dialog with a single widget "Run" to show up.
                def run_function(*args):
                    out = func()
                    if not isinstance(out, Exception):
                        self._record_macro(func.__name__, (), {})
                    if self._result_widget is not None:
                        self._result_widget.value = out
                    return out
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
                    
                    @mgui.called.connect
                    def _after_run(value):
                        if isinstance(value, Exception):
                            return None
                        inputs = _get_parameters(mgui)
                        self._record_macro(func.__name__, (), inputs)
                        self._record_parameter_history(func.__name__, inputs)
                        if self._close_on_run:
                            if not self._popup:
                                try:
                                    self.remove(func_obj_name)
                                except ValueError:
                                    pass
                            mgui.close()
                        if self._result_widget is not None:
                            self._result_widget.value = value
                        
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
                            @mgui.called.connect
                            def _close(value):
                                if not self._popup:
                                    self.remove(func_obj_name)
                                mgui.close()
                    else:
                        # If napari.Viewer was found, then create a magicgui as a dock widget when button is 
                        # pushed, and remove it when function call is finished (if close_on_run==True).
                        viewer: napari.Viewer
                        
                        if self._close_on_run:
                            @mgui.called.connect
                            def _close(value):
                                viewer.window.remove_dock_widget(mgui.parent)
                                mgui.close()
                                
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
    
    def objectName(self) -> str:
        """
        This function makes the object name discoverable by napari's `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()
    
    def show(self) -> None:
        super().show()
        self.native.activateWindow()
        return None

def _raise_error_in_msgbox(func, parent=None):
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            raise_error_msg(parent, title=e.__class__.__name__, msg=str(e))
            out = e
        return out
    
    return wrapped_func

def _write_log(func, parent=None):
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            log = [f'{func.__name__}: <span style="color: red; font-weight: bold;">{e.__class__.__name__}</span>',
                   f'{e}']
            out = e
        else:
            log = f'{func.__name__}: <span style="color: blue; font-weight: bold;">Pass</span>'
        finally:
            LOGGER.append(log)
        return out
    
    return wrapped_func

def _find_unique_name(name:str, viewer:"napari.Viewer"):
    orig_name = name
    i = 0
    while name in viewer.window._dock_widgets:
        name = orig_name + f"-{i}"
        i += 1
    return name

def _get_parameters(mgui):
    inputs = {param: getattr(mgui, param).value
              for param in mgui.__signature__.parameters.keys()
              }
    
    return inputs

class Macro(list):
    def __repr__(self):
        return "\n".join(self)