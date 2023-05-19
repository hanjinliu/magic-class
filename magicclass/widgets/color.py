from __future__ import annotations
from typing import Iterable
from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal as QtSignal

from magicgui.widgets.bases import ValueWidget
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.application import use_app
from .utils import merge_super_sigs


def rgba_to_html(rgba: Iterable[float]) -> str:
    code = "#" + "".join(hex(int(c * 255))[2:].upper().zfill(2) for c in rgba)
    if code.endswith("FF"):
        code = code[:-2]
    return code


# modified from napari/_qt/widgets/qt_color_swatch.py
class QColorSwatch(QtW.QFrame):
    colorChanged = QtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self.colorChanged.connect(self._update_swatch_style)
        self.setMinimumWidth(40)
        self._pressed_pos = None
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tooltip = lambda: rgba_to_html(self.getQColor().getRgbF())

    def heightForWidth(self, w: int) -> int:
        return int(w * 0.667)

    def _update_swatch_style(self, _=None) -> None:
        rgba = f'rgba({",".join(str(int(x*255)) for x in self._color)})'
        self.setStyleSheet("QColorSwatch {background-color: " + rgba + ";}")

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._pressed_pos = self.mapToGlobal(a0.pos())
        return super().mousePressEvent(a0)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        # moved?
        if self._pressed_pos is not None:
            pos = self.mapToGlobal(a0.pos())
            dx = self._pressed_pos.x() - pos.x()
            dy = self._pressed_pos.y() - pos.y()
            if dx**2 + dy**2 > 4:
                self._pressed_pos = None
        return super().mouseMoveEvent(a0)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Show QColorPopup picker when the user clicks on the swatch."""
        # inside the widget?
        if self._pressed_pos is None or not self.rect().contains(event.pos()):
            return None
        if event.button() == Qt.MouseButton.LeftButton:
            initial = self.getQColor()
            dlg = QtW.QColorDialog(initial, self)
            dlg.setOptions(QtW.QColorDialog.ColorDialogOption.ShowAlphaChannel)
            ok = dlg.exec_()
            if ok:
                self.setColor(dlg.selectedColor())
        self._pressed_pos = None

    def getQColor(self) -> QtGui.QColor:
        return QtGui.QColor.fromRgbF(*self._color)

    def setColor(self, color: QtGui.QColor) -> None:
        old_color = rgba_to_html(self._color)
        self._color = QtGui.QColor.getRgbF(color)
        if rgba_to_html(self._color) != old_color:
            self.colorChanged.emit()

    def event(self, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.ToolTip:
            event = QtGui.QHelpEvent(event)
            QtW.QToolTip.showText(event.globalPos(), self._tooltip(), self)
            return True
        return super().event(event)


class QColorLineEdit(QtW.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        import matplotlib.colors

        self._color_converter = matplotlib.colors.to_rgba

    def setText(self, color: str | Iterable[float]):
        """Set the text of the lineEdit using any ColorType.

        Colors will be converted to standard SVG spec names if possible,
        or shown as #RGBA hex if not.

        Parameters
        ----------
        color : ColorType
            Can be any ColorType recognized by our
            utils.colormaps.standardize_color.transform_color function.
        """
        if isinstance(color, QtGui.QColor):
            color = rgba_to_html(QtGui.QColor.getRgbF(color))
        elif not isinstance(color, str):
            color = rgba_to_html(color)

        super().setText(color)

    def getQColor(self) -> QtGui.QColor:
        """Get color as QtGui.QColor object"""
        rgba = self._color_converter(self.text())
        return QtGui.QColor.fromRgbF(*rgba)

    def setColor(self, color: QtGui.QColor | str):
        if isinstance(color, str):
            color = self._color_converter(color)
        elif isinstance(color, QtGui.QColor):
            color = QtGui.QColor.getRgbF(color)
        code = "#" + "".join(
            hex(int(round(c * 255)))[2:].upper().zfill(2) for c in color
        )
        if code.endswith("FF"):
            code = code[:-2]
        self.setText(code)


class QColorEdit(QtW.QWidget):
    colorChanged = QtSignal(tuple)

    def __init__(self, parent=None, value: str = "white"):
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        self._color_swatch = QColorSwatch(self)
        self._line_edit = QColorLineEdit(self)
        _layout.addWidget(self._color_swatch)
        _layout.addWidget(self._line_edit)
        self.setLayout(_layout)

        self._color_swatch.colorChanged.connect(self._on_swatch_changed)
        self._line_edit.editingFinished.connect(self._on_line_edit_edited)

        self._line_edit.setColor(value)
        self._color_swatch.setColor(self._line_edit.getQColor())

    def color(self):
        """Return the current color."""
        return self._color_swatch._color

    def setColor(self, color):
        """Set value as the current color."""
        if isinstance(color, QtGui.QColor):
            color = QtGui.QColor.getRgbF(color)
        self._line_edit.setText(color)
        color = self._line_edit.getQColor()
        self._color_swatch.setColor(color)

    def _on_line_edit_edited(self, _=None):
        text = self._line_edit.text()
        try:
            self._line_edit.setText(text)
        except ValueError:
            self._on_swatch_changed()
        else:
            qcolor = self._line_edit.getQColor()
            self._color_swatch.setColor(qcolor)

    def _on_swatch_changed(self, _=None):
        qcolor = self._color_swatch.getQColor()
        self._line_edit.setColor(qcolor)
        self.colorChanged.emit(self.color())


# See https://stackoverflow.com/questions/42820380/use-float-for-qslider
class QDoubleSlider(QtW.QSlider):
    changed = QtSignal(float)

    def __init__(self, parent=None, decimals: int = 3):
        super().__init__(parent=parent)
        self.scale = 10**decimals
        self.setOrientation(Qt.Orientation.Horizontal)
        self.valueChanged.connect(self.doubleValueChanged)

    def doubleValueChanged(self):
        value = float(super().value()) / self.scale
        self.changed.emit(value)

    def value(self):
        return float(super().value()) / self.scale

    def setValue(self, value):
        super().setValue(int(float(value) * self.scale))

    def setMinimum(self, value):
        return super().setMinimum(value * self.scale)

    def setMaximum(self, value):
        return super().setMaximum(value * self.scale)

    def singleStep(self):
        return float(super().singleStep()) / self.scale

    def setSingleStep(self, value):
        return super().setSingleStep(value * self.scale)


class QColorSlider(QtW.QWidget):
    colorChanged = QtSignal(tuple)

    def __init__(self, parent=None, value="white"):
        super().__init__(parent=parent)
        import matplotlib.colors

        self._color_converter = matplotlib.colors.to_rgba
        _layout = QtW.QVBoxLayout()
        self.setLayout(_layout)
        _layout.setContentsMargins(0, 0, 0, 0)
        self._qsliders = [
            self.addSlider("R"),
            self.addSlider("G"),
            self.addSlider("B"),
            self.addSlider("A"),
        ]

        self._color_edit = QColorEdit(self, value=value)

        @self._color_edit._line_edit.editingFinished.connect
        def _read_color_str(e=None):
            self.setColor(self._color_edit._line_edit.getQColor())

        self._color_edit._color_swatch.setEnabled(False)

        @self.colorChanged.connect
        def _set_color_swatch(color: QtGui.QColor):
            qcolor = QtGui.QColor.fromRgbF(*color)
            self._color_edit._color_swatch.setColor(qcolor)

        _layout.addWidget(self._color_edit)

    def addSlider(self, label: str):
        qlabel = QtW.QLabel(label)
        qlabel.setFixedWidth(15)
        qslider = QDoubleSlider()
        qslider.setMaximum(1.0)
        qslider.setSingleStep(0.001)
        qspinbox = QtW.QDoubleSpinBox()
        qspinbox.setMaximum(1.0)
        qspinbox.setSingleStep(0.001)
        qspinbox.setAlignment(Qt.AlignmentFlag.AlignRight)

        qspinbox.setButtonSymbols(QtW.QDoubleSpinBox.ButtonSymbols.NoButtons)
        qspinbox.setStyleSheet("background:transparent; border: 0;")

        qslider.changed.connect(qspinbox.setValue)
        qslider.changed.connect(lambda e: self.setColor(self.color()))
        qspinbox.editingFinished.connect(qslider.setValue)
        qspinbox.editingFinished.connect(lambda e: self.setColor(qspinbox.text()))

        _container = QtW.QWidget(self)
        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        _container.setLayout(layout)
        layout.addWidget(qlabel)
        layout.addWidget(qslider)
        layout.addWidget(qspinbox)

        self.layout().addWidget(_container)
        return qslider

    def color(self):
        """Return the current color."""
        return tuple(sl.value() for sl in self._qsliders)

    def setColor(self, color):
        """Set value as the current color."""
        if isinstance(color, QtGui.QColor):
            color = QtGui.QColor.getRgbF(color)
        elif isinstance(color, str):
            color = self._color_converter(color)
        self._color_edit.setColor(color)
        for sl, c in zip(self._qsliders, color):
            sl.setValue(c)
        self.colorChanged.emit(self.color())


class _ColorEdit(QBaseValueWidget):
    _qwidget: QColorEdit

    def __init__(self, **kwargs):
        super().__init__(QColorEdit, "color", "setColor", "colorChanged", **kwargs)


class _ColorSlider(QBaseValueWidget):
    _qwidget: QColorSlider

    def __init__(self, **kwargs):
        super().__init__(QColorSlider, "color", "setColor", "colorChanged", **kwargs)


@merge_super_sigs
class ColorEdit(ValueWidget):
    """
    A widget for editing colors.

    Parameters
    ----------
    value : tuple of float or str
        RGBA color, color code or standard color name.
    """

    def __init__(self, **kwargs):
        app = use_app()
        assert app.native
        kwargs["widget_type"] = _ColorEdit
        super().__init__(**kwargs)


@merge_super_sigs
class ColorSlider(ValueWidget):
    """
    A multi-slider for editing colors.

    Parameters
    ----------
    value : tuple of float or str
        RGBA color, color code or standard color name.
    """

    def __init__(self, **kwargs):
        app = use_app()
        assert app.native
        kwargs["widget_type"] = _ColorSlider
        super().__init__(**kwargs)
