from __future__ import annotations
from functools import wraps
import inspect
from magicgui import magicgui
from magicgui.widgets import Container, Label, PushButton
from qtpy.QtWidgets import QMessageBox
from .utils import iter_members, exec_app

# Check if napari is available so that layers are detectable from GUIs.
try:
    import napari
except ImportError:
    NAPARI_AVAILABLE = False
    def get_current_viewer() -> None:
        return None
else:
    NAPARI_AVAILABLE = True
    def get_current_viewer() -> "napari.Viewer"|None:
        try:
            viewer = napari.current_viewer()
        except AttributeError:
            viewer = None
        return viewer

# TODO: 
# - Make magicgui options partially selectable.


class BaseGui(Container):
    def __init__(self, layout:str= "vertical", close_on_run:bool=True, name=None):
        super().__init__(layout=layout, labels=False, name=name)
        self._current_dock_widget = None
        self._close_on_run = close_on_run
        self.native.setObjectName(self.__class__.__name__)
    
    def _convert_methods_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            doc = cls.__doc__.strip()
        else:
            doc = ""
        lbl = Label(value=doc)
        self.append(lbl)
        
        # Bind all the methods
        base_members = set(iter_members(BaseGui))
        for name in iter_members(cls):
            if name in base_members:
                continue
            func = getattr(self, name, None)
            if callable(func):
                self._convert_one_method_into_a_widget(func)
        
        return self
    
    def _convert_one_method_into_a_widget(self, func_):
        """
        Make a push button from a class method.
        """ 
        if not callable(func_):
            raise TypeError(f"{func_} is not callable")
        name = func_.__name__.replace("_", " ")
        
        button = PushButton(text=name)

        func = wrap_with_msgbox(func_, parent=self.native)
        # Strangely, signature must be updated like this. Otherwise, already wrapped member function
        # will have signature with "self".
        func.__signature__ = inspect.signature(func_)

        if func.__doc__:
            button.tooltip = func.__doc__.strip()
        if len(inspect.signature(func).parameters) == 0:
            def run_function(*args):
                return func()
            button.changed.connect(run_function)
        else:
            def update_mgui(*args):
                try:
                    mgui = magicgui(func)
                except Exception as e:
                    msg = f"Exception was raised during building magicgui.\n{e.__class__.__name__}: {e}"
                    raise_error_msg(self.native, msg=msg)
                viewer = get_current_viewer()
                
                if viewer is None:
                    mgui.show(True)
                    if self._close_on_run:
                        @mgui._call_button.changed.connect
                        def _(*args):
                            mgui.native.close()
                else:
                    if self._close_on_run:
                        def _close_widget(*args):
                            viewer.window.remove_dock_widget(self._current_dock_widget)
                            mgui.native.close()
                            self._current_dock_widget = None
                        
                        mgui._call_button.changed.connect(_close_widget, position="last")
                            
                    if self._current_dock_widget:
                        viewer.window.remove_dock_widget(self._current_dock_widget)
                    self._current_dock_widget = viewer.window.add_dock_widget(mgui, name=name)
                    self._current_dock_widget.setFloating(True)
                return None
            
            button.changed.connect(update_mgui)
        
        self.append(button)
        return None
    
    def show(self):
        super().show(run=False)
        self.native.activateWindow()
        exec_app()
        return None
    
    def objectName(self):
        return self.native.objectName()
    
def raise_error_msg(parent, title:str="Error", msg:str="error"):
    QMessageBox.critical(parent, title, msg, QMessageBox.Ok)
    return None

def wrap_with_msgbox(func, parent=None):
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            raise_error_msg(parent, title=e.__class__.__name__, msg=str(e))
        else:
            return out

    return wrapped_func