from __future__ import annotations
from functools import wraps
from typing import Callable
import inspect
from magicgui import magicgui
from magicgui.widgets import Container, Label
from magicgui.widgets._bases import Widget
from .utils import iter_members
from .widgets import PushButtonPlus, Separator, raise_error_msg

# Check if napari is available so that layers are detectable from GUIs.
try:
    import napari
except ImportError:
    NAPARI_AVAILABLE = False
else:
    NAPARI_AVAILABLE = True

# TODO: 
# - progress bar
# - some responses when function call finished
# - think of nesting magic-class
#- "exclusive" mode

class BaseGui(Container):
    def __init__(self, layout:str= "vertical", close_on_run:bool=True, popup:bool=True, name=None):
        super().__init__(layout=layout, labels=False, name=name)
        self._current_dock_widget = None
        self._close_on_run = close_on_run
        self._popup = popup
        self._parameter_history:dict[str, dict[str]] = {}
        self.native.setObjectName(self.__class__.__name__)
    
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
        if not isinstance(obj, Widget) and callable(obj):
            name = obj.__name__.replace("_", " ")
            button = PushButtonPlus(name=obj.__name__, text=name)
        
            func = wrap_with_msgbox(obj, parent=self.native)
            # Strangely, signature must be updated like this. Otherwise, already wrapped member function
            # will have signature with "self".
            func.__signature__ = inspect.signature(obj)

            # Prepare a button
            button.tooltip = func.__doc__.strip() if func.__doc__ else ""
            
            if len(inspect.signature(func).parameters) == 0:
                def run_function(*args):
                    return func()
            else:
                def run_function(*args):
                    func_obj_name = f"function-{id(func)}"
                    try:
                        mgui = magicgui(func)
                        mgui.name = func_obj_name
                        # Recover last inputs if exists.
                        params = self._parameter_history.get(func.__name__, {})
                        for key, value in params.items():
                            getattr(mgui, key).value = value
                            
                    except Exception as e:
                        msg = f"Exception was raised during building magicgui.\n{e.__class__.__name__}: {e}"
                        raise_error_msg(self.native, msg=msg)
                        return None
                    
                    viewer = None
                    if NAPARI_AVAILABLE:
                        try:
                            viewer = self.parent.parent().qt_viewer.viewer
                        except AttributeError:
                            pass
                    
                    if viewer is None:
                        # If napari.Viewer was not found, then open up a magicgui when button is pushed, and 
                        # close it when function call is finished (if close_on_run==True).
                        if self._popup:
                            mgui.show(True)
                        else:
                            sep = Separator(orientation="horizontal", text=name)
                            mgui.native.layout().insertWidget(0, sep.native)
                            self.append(mgui)
                            
                        if self._close_on_run:
                            @mgui._call_button.changed.connect
                            def _close_widget(*args):
                                inputs = {param: getattr(mgui, param).value
                                          for param in mgui.__signature__.parameters.keys()}
                                self._parameter_history.update({func.__name__: inputs})
                                if not self._popup:
                                    self.remove(func_obj_name)
                                mgui.native.close()
                    else:
                        # If napari.Viewer was found, then create a magicgui as a dock widget when button is 
                        # pushed, and remove it when function call is finished (if close_on_run==True).
                        if self._close_on_run:
                            def _close_widget(*args):
                                viewer.window.remove_dock_widget(self._current_dock_widget)
                                mgui.native.close()
                                self._current_dock_widget = None
                            
                            mgui._call_button.changed.connect(_close_widget, position="last")
                            
                        self._current_dock_widget = viewer.window.add_dock_widget(mgui, name=name)
                        self._current_dock_widget.setFloating(self._popup)
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
        This function make the object name discoverable by napari's `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()
    
    def show(self):
        super().show()
        self.native.activateWindow()
        return None
    

def wrap_with_msgbox(func, parent=None):
    """
    Wrapper for error handling during GUI running. Instead of raising error in console, show a message box.
    """    
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

def signature_to_button_design(options:dict[str], button:PushButtonPlus):
    for k, v in options.items():
        v = options.get(k, None)
        if v is not None:
            setattr(button, k, v)
    return None