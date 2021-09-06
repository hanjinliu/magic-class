from __future__ import annotations
import inspect
from magicgui import magicgui
from magicgui.widgets import Container, Label, PushButton
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
# - Error handling.


class BaseGui(Container):
    def __init__(self, layout:str= "vertical", close_on_run:bool=True, name=None):
        super().__init__(layout=layout, labels=False, name=name)
        self._current_dock_widget = None
        self._close_on_run = close_on_run
    
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
                self._bind_method(func)
        
        return self
    
    def _bind_method(self, func):
        """
        Make a push button from a class method.
        """ 
        if not callable(func):
            raise TypeError(f"{func} is not callable")
        name = func.__name__.replace("_", " ")
        
        button = PushButton(text=name)
        
        if func.__doc__:
            button.tooltip = func.__doc__.strip()
        if len(inspect.signature(func).parameters) == 0:
            def run_function(*args):
                return func()
            button.changed.connect(run_function)
        else:
            def update_mgui(*args):
                mgui = magicgui(func)
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