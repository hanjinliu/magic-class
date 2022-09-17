from __future__ import annotations
from psygnal import Signal
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt
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
        self._qtitlebar = _QTitleBar(title, parent=self.native)
        self.set_widget(self._qtitlebar)
        if button:
            self._qtitlebar.closeSignal.connect(
                lambda: self.btn_clicked.emit(self._qtitlebar.button().isDown())
            )
        else:
            self._qtitlebar.button().hide()
        self._title = title

    @property
    def btn_text(self):
        """The button text."""
        return self._qtitlebar.button().text()

    @btn_text.setter
    def btn_text(self, value: str):
        """Set the button text."""
        return self._qtitlebar.button().setText(value)

    @property
    def title(self) -> str:
        """The title string."""
        return self._qtitlebar.title()

    @title.setter
    def title(self, text: str):
        """Set the title string"""
        return self._qtitlebar.setTitle(text)


class _QTitleBar(QtW.QWidget):
    """A custom title bar"""

    closeSignal = Signal()

    def __init__(self, title: str = "", parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        _layout.setContentsMargins(1, 0, 1, 0)
        _layout.setSpacing(0)

        self._title_label = QtW.QLabel()
        self._title_label.setContentsMargins(0, 0, 0, 0)

        _frame = QtW.QFrame()
        _frame.setFrameShape(QtW.QFrame.Shape.HLine)
        _frame.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        _frame.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )
        self._close_button = QtW.QToolButton()
        self._close_button.setText("✕")
        self._close_button.setToolTip("Close the widget.")
        self._close_button.setFixedSize(QtCore.QSize(28, 28))
        self._close_button.setCursor(Qt.CursorShape.ArrowCursor)

        _layout.addWidget(self._title_label)
        _layout.addWidget(_frame)
        _layout.addWidget(self._close_button)
        _layout.setAlignment(self._close_button, Qt.AlignmentFlag.AlignRight)
        self.setLayout(_layout)

        self._close_button.clicked.connect(self.closeSignal.emit)

        self.setTitle(title)

    def button(self) -> QtW.QToolButton:
        return self._close_button

    def title(self) -> str:
        """The title text."""
        return self._title_label.text()

    def setTitle(self, text: str):
        """Set the title text."""
        if text == "":
            self._title_label.setVisible(False)
        else:
            self._title_label.setVisible(True)
            self._title_label.setText(f"{text}  ")
