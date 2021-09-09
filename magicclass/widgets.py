from __future__ import annotations
from qtpy.QtWidgets import QFrame, QLabel
from qtpy.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from magicgui.widgets import Container

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