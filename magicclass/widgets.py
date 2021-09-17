from __future__ import annotations
from typing import Callable, Iterable
from PyQt5.QtWidgets import QWidget
from qtpy.QtWidgets import QFrame, QLabel, QMessageBox, QPushButton, QGridLayout, QTextEdit
from qtpy.QtGui import QIcon, QFont
from qtpy.QtCore import QSize, Qt
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.colors import to_rgb
from magicgui.widgets import Container, PushButton, TextEdit

__all__ = ["raise_error_msg", "Figure", "Separator", "Logger", "PushButtonPlus"]

def raise_error_msg(parent, title:str="Error", msg:str="error"):
    QMessageBox.critical(parent, title, msg, QMessageBox.Ok)
    return None

class FrozenContainer(Container):
    """
    Non-editable container. 
    This class is useful to add QWidget into Container. If a QWidget is added via 
    Container.layout(), it will be invisible from Container. We can solve this
    problem by "wrapping" a QWidget with a Container.
    """    
    def insert(self, key, value):
        raise AttributeError(f"Cannot insert widget to {self.__class__.__name__}")
    
    def set_widget(self, widget:QWidget):
        self.native.layout().addWidget(widget)
        self.margins = (0, 0, 0, 0)
        return None

class Figure(FrozenContainer):
    def __init__(self, fig=None, layout="vertical", **kwargs):
        if fig is None:
            backend = mpl.get_backend()
            mpl.use("Agg")
            fig, _ = plt.subplots()
            mpl.use(backend)
        
        super().__init__(layout=layout, labels=False, **kwargs)
        canvas = FigureCanvas(fig)
        self.set_widget(canvas)
        self.figure = fig
        self.axes = fig.axes
        
    def draw(self):
        self.figure.canvas.draw()
    
    @property
    def ax(self):
        return self.axes[0]
        
class Separator(FrozenContainer):
    def __init__(self, orientation="horizontal", text:str="", name:str=""):
        super().__init__(layout=orientation, labels=False, name=name)
        main = QFrame(parent=self.native)
        main.setLayout(QGridLayout())
        
        line = QFrame(parent=main)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setContentsMargins(0, 0, 0, 0)
        main.layout().addWidget(line)
        
        if text:
            label = QLabel(text, parent=main)
            label.setContentsMargins(0, 0, 0, 0)
            label.setAlignment(Qt.AlignRight)
            main.layout().addWidget(label)
        
        self.set_widget(main)

class Logger(TextEdit):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.native: QTextEdit
        self.read_only = True
        self.native.setFont(QFont("Consolas"))
        self.n_line = 0
        
    def append(self, text:str|Iterable[str]):
        if isinstance(text, str):
            self.native.append(text)
            vbar = self.native.verticalScrollBar()
            vbar.setValue(vbar.maximum())
            self.n_line += 1
        else:
            for txt in text:
                self.append(txt)
        return None


class PushButtonPlus(PushButton):
    def __init__(self, text:str|None=None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native: QPushButton
        self._icon_path = None
    
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