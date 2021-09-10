from __future__ import annotations
from qtpy.QtWidgets import QFrame, QLabel, QMessageBox
from qtpy.QtGui import QIcon
from qtpy.QtCore import QSize, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from magicgui.widgets import Container, PushButton

def figure(fig) -> Container:
    canvas = FigureCanvas(fig)
    cnt = Container()
    cnt.native.layout().addWidget(canvas)
    return cnt

def h_separator(name:str="") -> Container:
    sep = Container(layout="horizontal")
    
    line = QFrame(parent=sep)
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    line.setContentsMargins(0, 0, 0, 0)
    sep.native.layout().addWidget(line)
    if name:
        label = QLabel(name, parent=sep)
        label.setContentsMargins(0, 0, 0, 0)
        label.setAlignment(Qt.AlignRight)
        sep.native.layout().addWidget(label)
    
    return sep

# def v_separator(parent=None, name:str="") -> QFrame:
#     sep = QFrame(parent)
#     sep.setLayout(QVBoxLayout())
#     line = QFrame(parent=sep)
#     line.setFrameShape(QFrame.VLine)
#     line.setFrameShadow(QFrame.Sunken)
#     line.setContentsMargins(0, 0, 0, 0)
#     sep.layout().addWidget(line)
#     if name:
#         label = QLabel(name, parent=sep)
#         label.setContentsMargins(0, 0, 0, 0)
#         label.setAlignment(Qt.AlignRight)
#         sep.layout().addWidget(label)
        
#     return sep


def raise_error_msg(parent, title:str="Error", msg:str="error"):
    QMessageBox.critical(parent, title, msg, QMessageBox.Ok)
    return None

class PushButtonPlus(PushButton):
    def __init__(self, text:str|None=None, **kwargs):
        super().__init__(text=text, **kwargs)
        self._icon_path = None
        
    @property
    def icon_path(self):
        return self._icon_path
    
    @icon_path.setter
    def icon_path(self, path:str):
        icon = QIcon(path)
        self.native.setIcon(icon)
    
    @property
    def font_size(self):
        return self.native.font().pointSize()
    
    @font_size.setter
    def font_size(self, size:int):
        font = self.native.font()
        font.setPointSize(size)
        self.native.setFont(font)
    
    @property
    def icon_size(self):
        qsize = self.native.iconSize()
        return qsize.width(), qsize.height()
        
    @icon_size.setter
    def icon_size(self, size:tuple[int, int]):
        w, h = size
        self.native.setIconSize(QSize(w, h))
    
    def from_options(self, options:dict[str]):
        for k, v in options.items():
            v = options.get(k, None)
            if v is not None:
                setattr(self, k, v)
        return None