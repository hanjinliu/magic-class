from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any
from pathlib import Path
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from qtpy.QtSvg import QSvgRenderer

import superqt

if TYPE_CHECKING:
    from .mgui_ext import PushButtonPlus, AbstractAction
    from magicgui.widgets import Widget


class _IconBase:
    _source: Any

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._source!r})"

    def get_qicon(self, dst: Widget | AbstractAction) -> QtGui.QIcon:
        raise NotImplementedError()

    def install(self, dst: PushButtonPlus | AbstractAction) -> None:
        icon = self.get_qicon(dst)
        dst.native.setIcon(icon)


class IconPath(_IconBase):
    """An object of an icon from a path."""

    def __init__(self, source: Any):
        self._source = str(source)

    def get_qicon(self, dst) -> QtGui.QIcon:
        return QtGui.QIcon(self._source)


def _color_for_palette(dst: Widget | AbstractAction) -> str:
    if isinstance(dst.native, QtW.QWidget):
        palette = dst.native.palette()
    elif isinstance(dst.native, QtW.QAction):
        if menu := dst.native.parent():
            palette = menu.palette()
        else:
            palette = None
    else:
        return "#333333"

    if palette is None:
        color = "#333333"
    else:
        # use foreground color
        color = palette.color(QtGui.QPalette.ColorRole.WindowText).name()
        # don't use full black or white
        color = {"#000000": "#333333", "#ffffff": "#cccccc"}.get(color, color)
    return color


class SVGBufferIconEngine(QtGui.QIconEngine):
    def __init__(self, xml: str | bytes) -> None:
        if isinstance(xml, str):
            xml = xml.encode("utf-8")
        self.data = QtCore.QByteArray(xml)
        super().__init__()

    def paint(self, painter: QtGui.QPainter, rect, mode, state):
        """Paint the icon int ``rect`` using ``painter``."""
        renderer = QSvgRenderer(self.data)
        renderer.setAspectRatioMode(QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        renderer.render(painter, QtCore.QRectF(rect))

    def clone(self):
        """Required to subclass abstract QIconEngine."""
        return SVGBufferIconEngine(self.data)

    def pixmap(self, size, mode, state):
        """Return the icon as a pixmap with requested size, mode, and state."""
        img = QtGui.QImage(size, QtGui.QImage.Format.Format_ARGB32)
        img.fill(QtCore.Qt.GlobalColor.transparent)
        pixmap = QtGui.QPixmap.fromImage(
            img, QtCore.Qt.ImageConversionFlag.NoFormatConversion
        )
        painter = QtGui.QPainter(pixmap)
        self.paint(painter, QtCore.QRect(QtCore.QPoint(0, 0), size), mode, state)
        return pixmap


class SvgIcon(IconPath):
    def __init__(self, source: Any):
        self._svg_text = Path(source).read_text()
        self._svg_text_orig = self._svg_text
        if "#000000" in self._svg_text:
            self._svg_text = self._svg_text.replace("#000000", "{color}")
            self._need_format = True
        elif "#FFFFFF" in self._svg_text:
            self._svg_text = self._svg_text.replace("#FFFFFF", "{color}")
            self._need_format = True
        else:
            self._need_format = False

    def get_qicon(self, dst: Widget | AbstractAction) -> QtGui.QIcon:
        if not self._need_format:
            return QtGui.QIcon(SVGBufferIconEngine(self._svg_text_orig))
        color = _color_for_palette(dst)
        try:
            return QtGui.QIcon(SVGBufferIconEngine(self._svg_text.format(color=color)))
        except (OSError, ValueError) as e:
            warnings.warn(f"Could not format icon: {e}", stacklevel=2)
            return QtGui.QIcon(SVGBufferIconEngine(self._svg_text_orig))


class ArrayIcon(_IconBase):
    """An object of an icon from numpy array."""

    _source: QtGui.QImage

    def __init__(self, source: Any):
        import numpy as np
        from magicgui.widgets._image import _mpl_image

        arr = np.asarray(source)
        img = _mpl_image.Image()
        img.set_data(arr)

        val: np.ndarray = img.make_image()
        h, w, _ = val.shape
        self._source = QtGui.QImage(val, w, h, QtGui.QImage.Format.Format_RGBA8888)

    def get_qicon(self, dst) -> QtGui.QIcon:
        if hasattr(dst.native, "size"):
            qsize = dst.native.size()
        else:
            qsize = QtCore.QSize(32, 32)
        qimg = self._source.scaled(
            qsize,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )

        qpix = QtGui.QPixmap.fromImage(qimg)
        return QtGui.QIcon(qpix)


class IconifyIcon(_IconBase):
    """Icon using iconify."""

    _source: str

    def __init__(self, source: Any):
        if ":" not in source:
            # for parity with the other backends, assume fontawesome
            # if no prefix is given.
            source = f"fa:{source}"

        self._source = source

    def get_qicon(self, dst) -> QtGui.QIcon:
        color = _color_for_palette(dst)
        try:
            return superqt.QIconifyIcon(self._source, color=color)
        except (OSError, ValueError) as e:
            warnings.warn(f"Could not set iconify icon: {e}", stacklevel=2)
            return QtGui.QIcon()


def get_icon(val: Any) -> _IconBase:
    """Get a proper icon object from a value."""
    if isinstance(val, _IconBase):
        icon = val
    elif isinstance(val, Path) or Path(val).exists():
        icon_path = Path(val)
        if icon_path.suffix == ".svg":
            icon = SvgIcon(icon_path)
        else:
            icon = IconPath(icon_path)
    elif hasattr(val, "__array__"):
        icon = ArrayIcon(val)
    elif isinstance(val, str):
        icon = IconifyIcon(val)
    else:
        raise TypeError(f"Input {val!r} cannot be converted to an icon.")
    return icon
