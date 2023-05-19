from __future__ import annotations
from typing import Any, TYPE_CHECKING
from PyQt5 import QtGui
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal as QtSignal

from magicgui.widgets.bases import ValueWidget
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.application import use_app
from .utils import merge_super_sigs
from .color import QColorSwatch

if TYPE_CHECKING:
    from magicclass.types import Color


class QColormapHandle(QtW.QFrame):
    dragged = QtSignal(float)
    dragFinished = QtSignal()
    colorChanged = QtSignal()

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.SubWindow)
        self._swatch = QColorSwatch(self)
        self._swatch.setFixedSize(10, 24)
        self._swatch.colorChanged.connect(self.colorChanged.emit)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._swatch)
        self.setLayout(layout)

        self.setFixedSize(14, 32)
        self._drag_start: QtCore.QPoint | None = None
        self._value = 0.0

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
    doubleClicked = QtSignal(QtCore.QPoint)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._cmap: dict[float, QtGui.QColor] = {
            0: QtGui.QColor(0, 0, 0),
            1: QtGui.QColor(255, 255, 255),
        }
        self.setMinimumWidth(120)
        self.setFixedHeight(18)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding,
            QtW.QSizePolicy.Policy.Minimum,
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _get_gradient(self) -> QtGui.QLinearGradient:
        grad = QtGui.QLinearGradient(0, 2, self.width(), 2)
        for pos, color in self._cmap.items():
            grad.setColorAt(pos, color)
        return grad

    def _make_brush(self) -> QtGui.QBrush:
        return QtGui.QBrush(self._get_gradient())

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setBrush(QtGui.QBrush(self._get_gradient()))
        rect = self.rect()
        painter.drawRect(rect)

    def colormap(self) -> dict[float, QtGui.QColor]:
        return self._cmap

    def setColormap(self, cmap: dict[float, QtGui.QColor]):
        self._cmap = cmap
        self.update()

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(a0.pos())
        return None


class QColormapEdit(QtW.QWidget):
    colormapChanged = QtSignal(dict)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(25, 10, 25, 10)
        self._qcmap = QColormap(self)
        self._handles: list[QColormapHandle] = []
        layout.addWidget(self._qcmap)
        self.setLayout(layout)

        self.addHandleAt(0, QtGui.QColor(0, 0, 0))
        self.addHandleAt(1, QtGui.QColor(255, 255, 255))
        self._update_colormap()

        self._qcmap.customContextMenuRequested.connect(self._show_cmap_context_menu)
        self._qcmap.doubleClicked.connect(self._add_section)

    def addHandleAt(self, val: float, color: QtGui.QColor):
        if not 0 <= val <= 1:
            raise ValueError("pos must be between 0 and 1")
        self._add_handle_no_check(val, color)
        self._sort_handle_list()
        self._update_colormap()
        return None

    def _add_handle_no_check(self, val: float, color: QtGui.QColor):
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
            int(val * (self._qcmap.width() + 1)) - hsize.width() // 2 + pos.x(),
            size.height() // 2 - hsize.height() // 2 + pos.y(),
        )
        handle.move(handle_pos)
        handle.dragged.connect(lambda delta: self._handle_dragged(handle, delta))
        handle.dragFinished.connect(self._sort_handle_list)
        handle._swatch.customContextMenuRequested.connect(
            lambda pos: self._show_color_context_menu(pos, handle)
        )

    def removeHandle(self, handle: QColormapHandle):
        if len(self._handles) <= 2:
            raise ValueError("Colormap must have more than one handle.")
        self._remove_handle_no_check(handle)
        self._update_colormap()
        return None

    def _remove_handle_no_check(self, handle: QColormapHandle):
        self._handles.remove(handle)
        handle.setParent(None)
        handle.deleteLater()
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

    def _sort_handle_list(self):
        # sort handles by its value
        self._handles.sort(key=lambda x: x.value())

    def _make_colormap(self) -> dict[float, QtGui.QColor]:
        cmap = {}
        for handle in self._handles:
            cmap[handle.value()] = handle.color()
        return cmap

    def _update_colormap(self):
        cmap = self._make_colormap()
        self._qcmap.setColormap(cmap)
        return None

    def _show_cmap_context_menu(self, pos: QtCore.QPoint) -> None:
        menu = QtW.QMenu(self)
        menu.addAction("Add section", lambda: self._add_section(pos))
        menu.exec(self._qcmap.mapToGlobal(pos))

    def _show_color_context_menu(
        self,
        pos: QtCore.QPoint,
        handle: QColormapHandle,
    ) -> None:
        menu = QtW.QMenu(self)
        action = menu.addAction(
            "Delete this section", lambda: self.removeHandle(handle)
        )
        if len(self._handles) == 2:
            action.setEnabled(False)
        menu.exec(handle._swatch.mapToGlobal(pos))

    def _add_section(self, pos: QtCore.QPoint) -> None:
        width = self._qcmap.width() + 1

        val = pos.x() / width
        val = max(0, min(val, 1))
        self.addHandleAt(val, self._color_at(pos))

    def _value_at(self, pos: QtCore.QPoint) -> float:
        width = self._qcmap.width() + 1
        return pos.x() / width

    def _color_at(self, pos: QtCore.QPoint) -> QtGui.QColor:
        val = self._value_at(pos)

        # linear interpolation
        cmap = self.colormap()
        clow = chigh = None
        ratio = val
        for v, col in cmap.items():
            if v > val:
                chigh = col
                break
            ratio = val - v
            clow = col
        if clow is None:
            return QtGui.QColor.fromRgbF(*chigh)
        if chigh is None:
            return QtGui.QColor.fromRgbF(*clow)
        return QtGui.QColor.fromRgbF(
            *[l * ratio + h * (1 - ratio) for l, h in zip(clow, chigh)]
        )

    def event(self, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.ToolTip:
            a0 = QtGui.QHelpEvent(a0)
            pos = self.mapToGlobal(a0.pos())
            localpos = self._qcmap.mapFromGlobal(pos)
            val = self._value_at(localpos)
            if 0 <= val <= 1:
                color = self._color_at(localpos)
                _r, _g, _b, _a = color.getRgb()
                txt = f"Position = {val:3f}\nR: {_r}\nG: {_g}\nB {_b}\n"
                if _a < 0:
                    txt *= f"\n {_a}"
                QtW.QToolTip.showText(pos, txt, self)
        elif a0.type() == QtCore.QEvent.Type.ParentChange:
            # get parent background color
            pal = self.parentWidget().palette()
            bg = pal.color(QtGui.QPalette.ColorRole.Background)
            if sum(bg.getRgb()) < 383:
                c0 = bg.lighter(120).name()
                c1 = bg.lighter(110).name()
            else:
                c0 = bg.darker(110).name()
                c1 = bg.darker(120).name()
            ss = f"qlineargradient( x1: 0 y1: 0, x2: 0 y2: 1, stop:0 {c0}, stop:1 {c1})"
            self.setStyleSheet(f"QColormapHandle {{ background: {ss}; }}")

        return super().event(a0)

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

    def setColormap(self, cmap: dict[float, str | tuple]):
        value = {}
        for k, v in cmap.items():
            if isinstance(v, str):
                color = QtGui.QColor(v)
            elif len(v) in (3, 4):
                color = QtGui.QColor.fromRgbF(*v)
            else:
                raise TypeError(f"{type(v)} not supported for a color.")
            value[k] = color
        self._qcmap.setColormap(value)
        while len(self._handles) > 0:
            self._remove_handle_no_check(self._handles[0])
        for k, col in value.items():
            self._add_handle_no_check(k, col)
        self._sort_handle_list()
        self._update_colormap()
        return None


# magicgui widgets


class _ColormapEdit(QBaseValueWidget):
    _qwidget: QColormapEdit

    def __init__(self, **kwargs):
        super().__init__(
            QColormapEdit, "colormap", "setColormap", "colormapChanged", **kwargs
        )

    def _pre_set_hook(self, value: Any) -> dict[float, Color]:
        if isinstance(value, dict):
            it = value.items()
        elif hasattr(value, "__iter__"):
            it = iter(value)
        else:
            raise TypeError(f"{type(value)} not supported for a colormap.")
        return dict(it)


@merge_super_sigs
class ColormapEdit(ValueWidget):
    """
    A widget for editing color maps.

    Parameters
    ----------
    value : dict of (float, color-type)
        Any color type
    """

    def __init__(self, **kwargs):
        app = use_app()
        assert app.native
        kwargs["widget_type"] = _ColormapEdit
        super().__init__(**kwargs)

    @property
    def colormap(self):
        from cmap import Colormap

        return Colormap(self.value)
