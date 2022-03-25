from __future__ import annotations
import vedo
from qtpy import QtWidgets as QtW
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from .const import AxesMode
from .components import Volume

from ...widgets import FreeWidget


class QtVtkCanvas(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        _layout = QtW.QVBoxLayout()
        self.setLayout(_layout)
        self._vtk_widget = QVTKRenderWindowInteractor(parent=self)
        self.plt = vedo.Plotter(qtWidget=self._vtk_widget, bg="black")
        self.plt.show()

        _layout.addWidget(self._vtk_widget)

    def add(self, actors):
        self.plt.add(actors)

    def remove(self, actors):
        self.plt.remove(actors)


class VtkCanvas(FreeWidget):
    def __init__(self):
        super().__init__()
        self._qwidget = QtVtkCanvas()
        self.set_widget(self._qwidget)
        self._layers = []
        self._axes = AxesMode.none

    @property
    def layers(self):
        return self._layers

    def add_volume(self, data):
        vol = Volume(data, self)
        self.layers.append(vol)
        self._qwidget.add(vol._current_obj)

    @property
    def axes(self):
        return self._axes.name

    @axes.setter
    def axes(self, v):
        self._qwidget.plt.axes = AxesMode(v).toint()
