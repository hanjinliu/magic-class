from __future__ import annotations
import weakref
import numpy as np
import vedo
from qtpy import QtWidgets as QtW
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from psygnal.containers import EventedList
from .const import AxesMode
from .volume import Volume
from .components import Mesh, VtkComponent, get_object_type

from ...widgets import FreeWidget
from ...types import Color


class QtVtkCanvas(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        _layout = QtW.QVBoxLayout()
        self.setLayout(_layout)
        self._vtk_widget = QVTKRenderWindowInteractor(parent=self)
        self.plt = vedo.Plotter(qtWidget=self._vtk_widget, bg="black", axes=0)
        self.plt.show()

        _layout.addWidget(self._vtk_widget)


class LayerList(EventedList):
    def __init__(self, data=(), parent: VtkCanvas = None):
        super().__init__(data=data)
        self._parent_ref = weakref.ref(parent)
        self.events.inserted.connect(self._on_inserted)
        self.events.removed.connect(self._on_removed)

    @property
    def parent(self) -> VtkCanvas:
        return self._parent_ref()

    def _on_inserted(self, i: int, obj: VtkComponent):
        self.parent._qwidget.plt.add(obj._obj)
        self.parent._qwidget.plt.window.Render()
        if len(self) == 1:
            self.parent._qwidget.plt.show(zoom=True)

    def _on_removed(self, i: int, obj: VtkComponent):
        self.parent._qwidget.plt.remove(obj._obj)
        self.parent._qwidget.plt.window.Render()
        if len(self) == 1:
            self.parent._qwidget.plt.show(zoom=True)


class VtkCanvas(FreeWidget):
    def __init__(self):
        """
        A Visualization toolkit (VTK) canvas for magicclass.

        This widget is useful for visualizing surface and mesh.
        """
        super().__init__()
        self._qwidget = QtVtkCanvas()
        self.set_widget(self._qwidget)
        self._layers = LayerList(parent=self)

    @property
    def layers(self):
        return self._layers

    def screenshot(self) -> np.ndarray:
        """Get screenshot as a numpy array."""
        pic: vedo.Picture = self._qwidget.plt.topicture()
        img = pic.tonumpy()
        return img

    def add_volume(
        self,
        volume: np.ndarray,
        color: Color = (0.7, 0.7, 0.7),
        mode: str = "iso",
    ):
        """
        Add a 3D volume to the canvas.

        Parameters
        ----------
        volume : np.ndarray
            Volume data. Must be 3D array.
        color : Color, optional
            Initial color of the volume.
        mode : str, default is "iso"
            Initial visualization mode of the volume.

        Returns
        -------
        Volume
            A volume layer.
        """
        vol = Volume(volume, _parent=self._qwidget.plt)
        self.layers.append(vol)
        self._qwidget.plt.add(vol._current_obj)
        vol.color = color
        vol.mode = mode
        if len(self.layers) == 1:
            self._qwidget.plt.show(zoom=True)
        return vol

    def add_object(self, *args, object_type: str = None, **kwargs):
        obj = get_object_type(object_type.capitalize())(
            *args, **kwargs, _parent=self._qwidget.plt
        )
        self.layers.append(obj)
        if len(self.layers) == 1:
            self._qwidget.plt.show()
        return obj

    def add_surface(self, data: tuple[np.ndarray, np.ndarray] | tuple[np.ndarray]):
        mesh = Mesh(data, _parent=self._qwidget.plt)
        self.layers.append(mesh)
        if len(self.layers) == 1:
            self._qwidget.plt.show(zoom=True)
        return mesh

    @property
    def axes(self) -> str:
        """The axes object."""
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
