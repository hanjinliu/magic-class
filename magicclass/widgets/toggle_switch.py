from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal, Property
from magicgui.widgets.bases import ButtonWidget
from magicgui.backends._qtpy.widgets import QBaseButtonWidget

# A iPhone style toggle switch.
# See https://stackoverflow.com/questions/14780517/toggle-switch-in-qt
class _QToggleSwitch(QtW.QAbstractButton):
    toggled = Signal(bool)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)

        self._height = 16
        self._brush = QtGui.QColor("#4D79C7")
        self.offset = self._height / 2
        self._checked = False
        self._margin = 3
        self._anim = QtCore.QPropertyAnimation(self, b"offset", self)

        self.setFixedWidth(38)

    @Property(QtGui.QColor)
    def brush(self):
        return self._brush

    @brush.setter
    def brush(self, brsh: QtGui.QBrush):
        self._brush = brsh

    @Property(int)
    def offset(self):
        return self._x

    @offset.setter
    def offset(self, o: int):
        self._x = o
        self.update()

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            2 * (self._height + self._margin), self._height + 2 * self._margin
        )

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        _y = self._height / 2
        rrect = QtCore.QRect(
            self._margin,
            self._margin,
            self.width() - 2 * self._margin,
            self.height() - 2 * self._margin,
        )
        if self.isEnabled():
            p.setBrush(self.brush if self._checked else Qt.GlobalColor.black)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            handle_color = QtGui.QColor("#d5d5d5")
        else:
            p.setBrush(Qt.GlobalColor.black)
            p.setOpacity(0.12)
            handle_color = QtGui.QColor("#BDBDBD")
        p.drawRoundedRect(rrect, _y, _y)
        p.setBrush(handle_color)
        p.setOpacity(1.0)
        p.drawEllipse(QtCore.QRectF(self.offset - _y, 0, self.height(), self.height()))

    def mouseReleaseEvent(self, e):
        if e.button() & Qt.MouseButton.LeftButton:
            self.setChecked(not self.checked())
        return super().mouseReleaseEvent(e)

    def enterEvent(self, e):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return super().enterEvent(e)

    def checked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        self._checked = val
        if self._checked:
            start = self._height / 2
            end = self.width() - self._height
        else:
            start = self.offset
            end = self._height / 2
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setDuration(120)
        self._anim.start()
        self.toggled.emit(self._checked)


class QToggleSwitch(QtW.QWidget):
    toggled = Signal(bool)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._switch = _QToggleSwitch(self)
        self._text = QtW.QLabel(self)
        layout.addWidget(self._switch)
        layout.addWidget(self._text)
        self.setLayout(layout)
        self._switch.toggled.connect(self.toggled)

    def checked(self):
        return self._switch.checked()

    def setChecked(self, val: bool):
        self._switch.setChecked(val)

    def text(self):
        return self._text.text()

    def setText(self, text: str):
        self._text.setText(text)


class ToggleSwitch(ButtonWidget):
    def __init__(self, **kwargs):
        super().__init__(
            widget_type=QBaseButtonWidget,
            backend_kwargs={"qwidg": QToggleSwitch},
            **kwargs,
        )
        self.native: QToggleSwitch
