from __future__ import annotations
import inspect
from magicgui import magicgui
from qtpy.QtWidgets import QPushButton, QWidget, QVBoxLayout, QLabel

# Check if napari is available so that layers are detectable from GUIs.
try:
    import napari
except ImportError:
    NAPARI_AVAILABLE = False
else:
    NAPARI_AVAILABLE = True

# TODO: change layout, make magicgui options partially selectable.

class BaseGui(QWidget):
    def __init__(self, parent=None):        
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        self._current_dock_widget = None
    
    def _convert_methods_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        lbl = QLabel(self)
        if cls.__doc__:
            lbl.setText(cls.__doc__.strip())
        self.layout().addWidget(lbl)
        
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
        
        button = QPushButton(name, parent=self)
        
        if func.__doc__:
            button.setToolTip(func.__doc__.strip())
        if len(inspect.signature(func).parameters) == 0:
            button.clicked.connect(func)
        else:
            def update_mgui(*args):
                mgui = magicgui(func)
                if NAPARI_AVAILABLE:
                    viewer = napari.current_viewer()
                else:
                    viewer = None
                
                if viewer is None:
                    mgui.show(True)
                else:
                    if self._current_dock_widget:
                        viewer.window.remove_dock_widget(self._current_dock_widget)
                    self._current_dock_widget = viewer.window.add_dock_widget(mgui, name=name)
                    self._current_dock_widget.setFloating(True)
                return None
            
            button.clicked.connect(update_mgui)
        
        self.layout().addWidget(button)
        return None