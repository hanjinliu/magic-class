from __future__ import annotations
from magicgui.events import Signal
from qtpy.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QHBoxLayout
from .utils import FrozenContainer

class Separator(FrozenContainer):
    btn_clicked = Signal(bool)
    def __init__(self, orientation="horizontal", text:str="", name:str="", button:bool=False):
        super().__init__(layout=orientation, labels=False, name=name)
        self._qtitlebar = _QTitleBar(self.native, text, button)
        self.set_widget(self._qtitlebar)
        if button:
            self._qtitlebar.button.clicked.connect(
                lambda e: self.btn_clicked.emit(self._qtitlebar.button.isDown())
                )
    
    @property
    def btn_text(self):
        return self._qtitlebar.button.text()
    
    @btn_text.setter
    def btn_text(self, value: str):
        self._qtitlebar.button.setText(value)
        
class _QTitleBar(QLabel):
    """
    See also: napari/_qt/qt_main_window.py.
    """
    def __init__(self, parent, text: str = "", button: bool = False):
        super().__init__(parent)

        line = QFrame(parent=self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        layout = QHBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(8, 1, 8, 0)
        
        if button:
            self.button = QPushButton(self)
            self.button.setFixedWidth(20)
            self.button.setStyleSheet("QPushButton {"
                                      "border: 1px solid #555;"
                                      "border-radius: 10px;"
                                      "border-style: outset;"
                                      "padding: 5px"
                                      "}")
            layout.addWidget(self.button)
        
        layout.addWidget(line)
        
        if text:
            text = QLabel(text, self)
            text.setSizePolicy(
                QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
            )
            layout.addWidget(text)

        self.setLayout(layout)

    def sizeHint(self):
        szh = super().sizeHint()
        szh.setHeight(20)
        return szh
    