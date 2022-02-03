from __future__ import annotations
from typing import Iterable
from qtpy.QtWidgets import QLineEdit, QColorDialog, QFrame, QWidget, QHBoxLayout
from qtpy.QtGui import QColor
from qtpy.QtCore import Qt, Signal as QtSignal

from magicgui.widgets import Container, FloatSlider
from magicgui.widgets._bases.value_widget import ValueWidget
from magicgui.widgets._concrete import merge_super_sigs
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.application import use_app

def rgba_to_qcolor(rgba: Iterable[float]) -> QColor:
    return QColor(*[255*c for c in rgba])

def qcolor_to_rgba(qcolor: QColor) -> tuple[float, float, float, float]:
    return tuple(c/255 for c in qcolor.getRgb())

def rgba_to_html(rgba: Iterable[float]) -> str:
    code = "#" + "".join(hex(int(c*255))[2:].upper().zfill(2) for c in rgba)
    if code.endswith("FF"):
        code = code[:-2]
    return code

# modified from napari/_qt/widgets/qt_color_swatch.py
class QColorSwatch(QFrame):
    colorChanged = QtSignal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._color: tuple[float, float, float, float] = (0., 0., 0., 0.)
        self.colorChanged.connect(self._update_swatch_style)
        self.setMinimumWidth(40)
    
    def heightForWidth(self, w: int) -> int:
        return int(w*0.667)

    def _update_swatch_style(self, _=None) -> None:
        rgba = f'rgba({",".join(str(int(x*255)) for x in self._color)})'
        self.setStyleSheet('QColorSwatch {background-color: ' + rgba + ';}')

    def mouseReleaseEvent(self, event):
        """Show QColorPopup picker when the user clicks on the swatch."""
        if event.button() == Qt.LeftButton:
            initial = self.getQColor()
            dlg = QColorDialog(initial, self)
            dlg.setOptions(QColorDialog.ShowAlphaChannel)
            ok = dlg.exec_()
            if ok:
                self.setColor(dlg.selectedColor())
            

    def getQColor(self) -> QColor:
        return rgba_to_qcolor(self._color)
        
    def setColor(self, color: QColor) -> None:
        old_color = rgba_to_html(self._color)
        self._color = qcolor_to_rgba(color)
        if rgba_to_html(self._color) != old_color:
            self.colorChanged.emit()


class QColorLineEdit(QLineEdit):
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
        if isinstance(color, QColor):
            color = rgba_to_html(qcolor_to_rgba(color))
        elif not isinstance(color, str):
            color = rgba_to_html(color)
        
        super().setText(color)
    
    def getQColor(self) -> QColor:
        """Get color as QColor object"""
        rgba = self._color_converter(self.text())
        return rgba_to_qcolor(rgba)
        
    def setColor(self, color: QColor | str):
        if isinstance(color, str):
            color = self._color_converter(color)
        elif isinstance(color, QColor):
            color = qcolor_to_rgba(color)
        code = "#" + "".join(hex(int(c*255))[2:].upper().zfill(2) for c in color)
        if code.endswith("FF"):
            code = code[:-2]
        self.setText(code)
        

class QColorEdit(QWidget):
    colorChanged = QtSignal(tuple)
    
    def __init__(self, parent=None, value: str = "white"):
        super().__init__(parent)
        _layout = QHBoxLayout()
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
        if isinstance(color, QColor):
            color = qcolor_to_rgba(color)
        self._line_edit.setText(color)
        self.colorChanged.emit(self.color())


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


class _ColorEdit(QBaseValueWidget):
    _qwidget: QColorEdit
    
    def __init__(self):
        super().__init__(QColorEdit, "color", "setColor", "colorChanged")

@merge_super_sigs
class ColorEdit(ValueWidget):
    """
    A widget for editing colors.
    
    Parameters
    ----------
    value : tuple of float
        
    """
    def __init__(self, **kwargs):
        app = use_app()
        assert app.native
        kwargs["widget_type"] = _ColorEdit
        super().__init__(**kwargs)
        self.native._on_line_edit_edited()

@merge_super_sigs
class ColorSlider(Container):
    def __init__(self, value="white"):
        self.sliders: list[FloatSlider] = [
            FloatSlider(min=0, max=1, step=0.001, label="R"),
            FloatSlider(min=0, max=1, step=0.001, label="G"),
            FloatSlider(min=0, max=1, step=0.001, label="B"),
            FloatSlider(min=0, max=1, step=0.001, label="A"),
            ]
        self.color_edit = ColorEdit(label="Color")
        self.color_edit.enabled = False
        super().__init__(layout="vertical", 
                         widgets = self.sliders + [self.color_edit]
                         )
        for sl in self.sliders:
            @sl.changed.connect
            def _():
                self.color_edit.value = self.value
                self.color_edit.native._on_line_edit_edited()
                self.color_edit.native._on_swatch_changed()
        
        self.value = value
    
    @property
    def value(self) -> tuple[float, float, float, float]:
        return tuple(sl.value for sl in self.sliders)
    
    @value.setter
    def value(self, color):
        self.color_edit.value = color
        value = self.color_edit.value
        for sl, v in zip(self.sliders, value):
            sl.value = v
