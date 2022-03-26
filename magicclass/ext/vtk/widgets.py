from __future__ import annotations
import vedo
from qtpy import QtWidgets as QtW
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from .const import AxesMode
from .volume import Volume
from .components import get_object_type

from ...widgets import FreeWidget


class QtVtkCanvas(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        _layout = QtW.QVBoxLayout()
        self.setLayout(_layout)
        self._vtk_widget = QVTKRenderWindowInteractor(parent=self)
        self.plt = vedo.Plotter(qtWidget=self._vtk_widget, bg="black", axes=0)
        self.plt.show()

        _layout.addWidget(self._vtk_widget)


class VtkCanvas(FreeWidget):
    def __init__(self):
        super().__init__()
        self._qwidget = QtVtkCanvas()
        self.set_widget(self._qwidget)
        self._layers = []

    @property
    def layers(self):
        return self._layers

    def add_volume(self, data):
        vol = Volume(data, self)
        self.layers.append(vol)
        self._qwidget.plt.add(vol._current_obj)
        if len(self.layers) == 1:
            self._qwidget.plt.show(zoom=True)

    def add_object(self, *args, object_type=None, **kwargs):
        obj = get_object_type(object_type)(*args, **kwargs, _parent=self._qwidget.plt)
        self.layers.append(obj)
        self._qwidget.plt.add(obj._obj)
        if len(self.layers) == 1:
            self._qwidget.plt.show()

    @property
    def axes(self):
        return AxesMode(self._qwidget.plt.axes).name

    @axes.setter
    def axes(self, v):
        if self._qwidget.plt.axes_instances:
            current_axes = self._qwidget.plt.axes_instances[0]
        else:
            current_axes = None
        a = getattr(AxesMode, v).value
        try:
            self._qwidget.plt.remove(current_axes)
        except TypeError:
            current_axes.EnabledOff()
        self._qwidget.plt.axes_instances = [None]
        self._qwidget.plt.show(axes=a)
