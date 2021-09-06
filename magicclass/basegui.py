from __future__ import annotations
import inspect
from magicgui import magicgui
from magicgui.widgets import Container, Label, PushButton

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

# TODO: make magicgui options partially selectable.

class BaseGui(Container):
    def __init__(self, layout:str= "vertical", name=None):
        super().__init__(layout=layout, labels=False, name=name)
        self._current_dock_widget = None
        
    
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
        base_members = [name for name, _ in inspect.getmembers(BaseGui)]
        for name, _ in inspect.getmembers(cls):
            if name.startswith("_") or name in base_members:
                continue
            func = getattr(self, name, None)
            if callable(func):
                self._bind_method(func)
        
        return self
    
    def _bind_method(self, func, name=None):
        """
        Make a push button from a class method.
        """ 
        if not callable(func):
            raise TypeError(f"{func} is not callable")
        if name is None:
            name = func.__name__.replace("_", " ")
        
        button = PushButton(text=name)
        
        if func.__doc__:
            button.tooltip = func.__doc__.strip()
        if len(inspect.signature(func).parameters) == 0:
            button.changed.connect(func)
        else:
            def update_mgui(*args):
                mgui = magicgui(func)
                mgui._call_button.changed.connect(lambda x: mgui.native.close())
                viewer = get_current_viewer()
                
                if viewer is None:
                    mgui.show(True)
                else:
                    if self._current_dock_widget:
                        viewer.window.remove_dock_widget(self._current_dock_widget)
                    self._current_dock_widget = viewer.window.add_dock_widget(mgui, name=name)
                    self._current_dock_widget.setFloating(True)
                return None
            
            button.changed.connect(update_mgui)
        
        self.append(button)
        return None
    