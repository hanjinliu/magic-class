from __future__ import annotations
from psygnal import Signal
from qtpy.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QHBoxLayout
from .utils import FreeWidget


class Separator(FreeWidget):
    """
    A Separator widget that can be used in both widgets and menus.
    This widget is not actually added to menus or toolbars.
    """

    btn_clicked = Signal(bool)

    def __init__(
        self,
        orientation: str = "horizontal",
        title: str = "",
        name: str = "",
        button: bool = False,
    ):
        super().__init__(name=name)
        self._qtitlebar = _QTitleBar(self.native, title, button)
        self.set_widget(self._qtitlebar)
        if button:
            self._qtitlebar.button.clicked.connect(
                lambda e: self.btn_clicked.emit(self._qtitlebar.button.isDown())
            )
        self._title = title

    @property
    def btn_text(self):
        return self._qtitlebar.button.text()

    @btn_text.setter
    def btn_text(self, value: str):
        self._qtitlebar.button.setText(value)

    @property
    def title(self) -> str:
        return self._title


class _QTitleBar(QLabel):
    """See also: napari/_qt/qt_main_window.py."""

    def __init__(self, parent, text: str = "", button: bool = False):
        super().__init__(parent)

        line = QFrame(parent=self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("Separator")
        line.setStyleSheet(
            """
            QFrame#Separator {
                background-color: gray;
            }
        """
        )

        layout = QHBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(8, 1, 8, 0)

        if button:
            self.button = QPushButton(self)
            self.button.setFixedWidth(20)
            self.button.setStyleSheet(
                "QPushButton {"
                "border: 1px solid #555;"
                "border-radius: 10px;"
                "border-style: outset;"
                "padding: 5px"
                "}"
            )
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
