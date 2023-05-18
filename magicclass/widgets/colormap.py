from __future__ import annotations
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QWidget
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal as QtSignal

from magicgui.widgets.bases import ValueWidget
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.application import use_app
from .utils import merge_super_sigs
from .color import QColorSwatch


class QColormapHandle(QtW.QFrame):
    dragged = QtSignal(float)
    dragFinished = QtSignal()
    colorChanged = QtSignal()

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.SubWindow)
        self.setStyleSheet("QColormapHandle { background-color: #212121; }")
        self.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        self._swatch = QColorSwatch(self)
        self._swatch.setFixedSize(16, 24)
        self._swatch.colorChanged.connect(self.colorChanged.emit)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._swatch)
        self.setLayout(layout)

        self.setFixedSize(20, 32)
        self._drag_start: QtCore.QPoint | None = None
        self._value = 0.0

        # https://stackoverflow.com/questions/48100574/how-to-create-a-qwidget-with-a-triangle-shape
        # _path = QtGui.QPainterPath()
        # _path.moveTo(QtCore.QPoint(20, 20))
        # _path.lineTo(QtCore.QPoint(80, 20))
        # _path.lineTo(QtCore.QPoint(50, 80))
        # _path.lineTo(QtCore.QPoint(20, 20))
        # self._region = QtGui.QRegion(QtGui.QPolygonF(_path))
        # self.setMask(self._region)

    def color(self) -> QtGui.QColor:
        return self._swatch.getQColor()

    def setColor(self, color: QtGui.QColor):
        self._swatch.setColor(color)

    def value(self) -> float:
        return self._value

    def setValue(self, value: float):
        self._value = value

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._drag_start = a0.pos()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if self._drag_start is None:
            return None
        delta = a0.pos().x() - self._drag_start.x()
        self.dragged.emit(delta)
        return None

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._drag_start = None
        self.dragFinished.emit()


class QColormap(QtW.QLabel):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._cmap: dict[float, QtGui.QColor] = {
            0: QtGui.QColor(0, 0, 0),
            1: QtGui.QColor(255, 255, 255),
        }
        self.setMinimumWidth(120)

    def _make_brush(self) -> QtGui.QBrush:
        grad = QtGui.QLinearGradient(0, 2, self.width(), 2)
        for pos, color in self._cmap.items():
            grad.setColorAt(pos, color)
        return QtGui.QBrush(grad)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setBrush(self._make_brush())
        rect = self.rect()
        painter.drawRect(rect)

    def colormap(self) -> dict[float, QtGui.QColor]:
        return self._cmap

    def setColormap(self, cmap: dict[float, QtGui.QColor]):
        self._cmap = cmap
        self.update()


class QColormapEdit(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        self._qcmap = QColormap(self)
        self._handles: list[QColormapHandle] = []
        layout.addWidget(self._qcmap)
        self.setLayout(layout)

        self.addHandleAt(0, QtGui.QColor(0, 0, 0))
        self.addHandleAt(1, QtGui.QColor(255, 255, 255))
        self._update_colormap()

    def addHandleAt(self, val: float, color: QtGui.QColor):
        if not 0 <= val <= 1:
            raise ValueError("pos must be between 0 and 1")
        handle = QColormapHandle(self)
        handle.colorChanged.connect(self._update_colormap)
        handle.setColor(color)
        handle.setValue(val)
        handle.show()
        hsize = handle.size()
        size = self._qcmap.size()
        self._handles.append(handle)
        pos = self._qcmap.pos()
        handle_pos = QtCore.QPoint(
            val * (self._qcmap.width() + 1) - hsize.width() // 2 + pos.x(),
            size.height() // 2 - hsize.height() // 2 + pos.y(),
        )
        handle.move(handle_pos)
        handle.dragged.connect(lambda delta: self._handle_dragged(handle, delta))
        return None

    def _handle_dragged(self, handle: QColormapHandle, delta: float):
        width = self._qcmap.width() + 1
        pos = self._qcmap.pos()
        hx = handle.pos().x() + delta + handle.width() // 2
        hx = max(pos.x(), min(hx, pos.x() + width))
        dist = hx - pos.x()
        value = dist / width
        handle.setValue(value)
        handle.move(
            int(hx) - handle.width() // 2, self.height() // 2 - handle.height() // 2
        )
        self._update_colormap()
        return None

    def _make_colormap(self) -> dict[float, QtGui.QColor]:
        cmap = {}
        for handle in self._handles:
            cmap[handle.value()] = handle.color()
        return cmap

    def _update_colormap(self):
        cmap = self._make_colormap()
        self._qcmap.setColormap(cmap)
        return None

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        pos = self._qcmap.pos()
        width = self._qcmap.width() + 1
        for handle in self._handles:
            val = handle.value()
            handle.move(
                int(val * width - handle.width() // 2 + pos.x()),
                self.height() // 2 - handle.height() // 2,
            )
        return super().resizeEvent(a0)

    def colormap(self) -> dict[float, tuple[float, float, float, float]]:
        return {k: v.getRgbF() for k, v in self._qcmap.colormap().items()}

    def setColormap(self, cmap: dict[float, tuple[float, float, float, float]]):
        self._qcmap.setColormap({k: QtGui.QColor.fromRgbF(*v) for k, v in cmap.items()})
        return None
