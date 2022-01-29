from __future__ import annotations
from typing import Iterable
from qtpy.QtWidgets import QLineEdit, QColorDialog, QFrame, QWidget, QHBoxLayout
from qtpy.QtGui import QColor
from qtpy.QtCore import Qt, Signal
from .utils import FreeWidget

from magicgui.widgets._bases.value_widget import UNSET

def rgba_to_qcolor(rgba):
    return QColor(*[255*c for c in rgba])

# modified from napari/_qt/widgets/qt_color_swatch.py
class QColorSwatch(QFrame):
    colorChanged = Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._color: tuple[float, float, float, float] = [0., 0., 0., 0.]
        self.colorChanged.connect(self._update_swatch_style)
        self.setMinimumWidth(20)
    
    def heightForWidth(self, a0: int) -> int:
        return int(a0*0.667)

    def _update_swatch_style(self, _=None) -> None:
        rgba = f'rgba({",".join(str(int(x*255)) for x in self._color)})'
        self.setStyleSheet('QColorSwatch {background-color: ' + rgba + ';}')

    def mouseReleaseEvent(self, event):
        """Show QColorPopup picker when the user clicks on the swatch."""
        if event.button() == Qt.LeftButton:
            initial = self.getQColor()
            dlg = QColorDialog(initial, self)
            dlg.setOptions(QColorDialog.ShowAlphaChannel)
            dlg.colorSelected.connect(self.setColor)
            dlg.exec_()
            

    def getQColor(self) -> QColor:
        return rgba_to_qcolor(self._color)
        
    def setColor(self, color: QColor) -> None:
        self._color = tuple(c/255 for c in color.getRgb())
        self.colorChanged.emit()


class QColorLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        import matplotlib.colors as mplcolor
        self._color_converter = mplcolor.to_rgba

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
        if not isinstance(color, str):
            color = rgba_to_qcolor(color)
        
        super().setText(color)
    
    def getQColor(self) -> QColor:
        rgba = self._color_converter(self.text())
        return rgba_to_qcolor(rgba)
        
    def setColor(self, color: QColor | str):
        if isinstance(color, str):
            color = self._color_converter(color)
        elif isinstance(color, QColor):
            color = tuple(c/255 for c in color.getRgb())
        code = "#" + "".join(hex(int(c*255))[2:].upper().zfill(2) for c in color)
        if code.endswith("FF"):
            code = code[:-2]
        self.setText(code)
        

class QColorEdit(QWidget):
    def __init__(self, parent, value: str):
        super().__init__(parent)
        _layout = QHBoxLayout()
        self._color_swatch = QColorSwatch(self)
        self._line_edit = QColorLineEdit(self)
        _layout.addWidget(self._color_swatch)
        _layout.addWidget(self._line_edit)
        self.setLayout(_layout)
        
        self._color_swatch.colorChanged.connect(self._on_swatch_changed)
        self._line_edit.editingFinished.connect(self._on_line_edit_edited)
        
        self._line_edit.setText(value)
        self._color_swatch.setColor(self._line_edit.getQColor())
    
    @property
    def color(self):
        """Return the current color."""
        return self._color_swatch._color

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


class ColorEdit(FreeWidget):
    def __init__(self, value=UNSET, **kwargs):
        super().__init__(**kwargs)
        if value is UNSET:
            value = "white"
        self.set_widget(QColorEdit(parent=None, value=value))
        self.central_widget: QColorEdit
    
    @property
    def value(self) -> tuple[float, float, float, float]:
        return self.central_widget.color
    
    @value.setter
    def value(self, color):
        self.central_widget._line_edit.setText(color)