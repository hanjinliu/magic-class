from __future__ import annotations
from typing import Callable, Iterable, Any
import re
from qtpy.QtWidgets import QPushButton
from qtpy.QtGui import QIcon
from qtpy.QtCore import QSize
from magicgui.widgets import Container, PushButton, FunctionGui
from magicgui.widgets._function_gui import _function_name_pointing_to_widget
from matplotlib.colors import to_rgb

# magicgui widgets that need to be extended to fit into magicclass

class FunctionGuiPlus(FunctionGui):
    """
    FunctionGui class with a parameter recording functionality.
    """
    def __call__(self, *args: Any, **kwargs: Any):
        sig = self.__signature__
        try:
            bound = sig.bind(*args, **kwargs)
        except TypeError as e:
            if "missing a required argument" in str(e):
                match = re.search("argument: '(.+)'", str(e))
                missing = match.groups()[0] if match else "<param>"
                msg = (
                    f"{e} in call to '{self._callable_name}{sig}'.\n"
                    "To avoid this error, you can bind a value or callback to the "
                    f"parameter:\n\n    {self._callable_name}.{missing}.bind(value)"
                    "\n\nOr use the 'bind' option in the magicgui decorator:\n\n"
                    f"    @magicgui({missing}={{'bind': value}})\n"
                    f"    def {self._callable_name}{sig}: ..."
                )
                raise TypeError(msg) from None
            else:
                raise

        bound.apply_defaults()
        self._previous_bound = bound # This is very important!!

        self._tqdm_depth = 0  # reset the tqdm stack count
        with _function_name_pointing_to_widget(self):
            value = self._function(*bound.args, **bound.kwargs)

        self._call_count += 1
        if self._result_widget is not None:
            with self._result_widget.changed.blocked():
                self._result_widget.value = value

        return_type = sig.return_annotation
        if return_type:
            from magicgui.type_map import _type2callback

            for callback in _type2callback(return_type):
                callback(self, value, return_type)
        self.called.emit(value)
        return value

class PushButtonPlus(PushButton):
    """
    A Qt specific PushButton widget with a magicgui bound.
    """    
    def __init__(self, text:str|None=None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native: QPushButton
        self._icon_path = None
        self.mgui: Container = None
    
    @property
    def background_color(self):
        return self.native.palette().button().color().getRgb()
    
    @background_color.setter
    def background_color(self, color:str|Iterable[float]):
        # TODO: In napari stylesheet is somehow overwritten and all the colored button will be "flat" 
        # (not shadowed when clicked/toggled)
        stylesheet = self.native.styleSheet()
        d = _stylesheet_to_dict(stylesheet)
        d.update({"background-color": _to_rgb(color)})
        stylesheet = _dict_to_stylesheet(d)
        self.native.setStyleSheet(stylesheet)
        
    @property
    def icon_path(self):
        return self._icon_path
    
    @icon_path.setter
    def icon_path(self, path:str):
        icon = QIcon(path)
        self.native.setIcon(icon)
    
    @property
    def icon_size(self):
        qsize = self.native.iconSize()
        return qsize.width(), qsize.height()
        
    @icon_size.setter
    def icon_size(self, size:tuple[int, int]):
        w, h = size
        self.native.setIconSize(QSize(w, h))
    
    @property
    def font_size(self):
        return self.native.font().pointSize()
    
    @font_size.setter
    def font_size(self, size:int):
        font = self.native.font()
        font.setPointSize(size)
        self.native.setFont(font)
        
    @property
    def font_color(self):
        return self.native.palette().text().color().getRgb()
    
    @font_color.setter
    def font_color(self, color:str|Iterable[float]):
        stylesheet = self.native.styleSheet()
        d = _stylesheet_to_dict(stylesheet)
        d.update({"color": _to_rgb(color)})
        stylesheet = _dict_to_stylesheet(d)
        self.native.setStyleSheet(stylesheet)

    @property
    def font_family(self):
        return self.native.font().family()
    
    @font_family.setter
    def font_family(self, family:str):
        font = self.native.font()
        font.setFamily(family)
        self.native.setFont(font)
    
    def from_options(self, options: dict[str] | Callable):
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

def _to_rgb(color):
    if isinstance(color, str):
        color = to_rgb(color)
    rgb = ",".join(str(max(min(int(c*255), 255), 0)) for c in color)
    return f"rgb({rgb})"

def _stylesheet_to_dict(stylesheet:str):
    if stylesheet == "":
        return {}
    lines = stylesheet.split(";")
    d = dict()
    for line in lines:
        k, v = line.split(":")
        d[k.strip()] = v.strip()
    return d

def _dict_to_stylesheet(d:dict):
    stylesheet = [f"{k}: {v}" for k, v in d.items()]
    return ";".join(stylesheet)