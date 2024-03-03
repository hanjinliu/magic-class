from __future__ import annotations

from typing import TYPE_CHECKING
import weakref
import numpy as np
from qtpy import QtWidgets as QtW, QtGui
import vedo

if TYPE_CHECKING:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
else:
    from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from psygnal.containers import EventedList
from .const import AxesMode
from .volume import Volume
from .components import Mesh, VedoComponent, get_object_type, Points

from magicclass.widgets import FreeWidget
from magicclass.types import Color


class QtVedoCanvas(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(_layout)
        vedo.settings.default_backend = "vtk"  # Avoid using Jupyter backend
        self._vtk_widget = QVTKRenderWindowInteractor(parent=self)
        self._plt = vedo.Plotter(qt_widget=self._vtk_widget, bg="bb", axes=0)
        # self._vtk_widget.GetRenderWindow().SetSize(1000, 1000) # no effect
        self._plt.show()

        _layout.addWidget(self._vtk_widget)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self._vtk_widget.close()
        return super().closeEvent(a0)


class LayerList(EventedList[VedoComponent]):
    def __init__(self, data=(), parent: VedoCanvas = None):
        super().__init__(data=data)
        self._parent_ref = weakref.ref(parent)
        self.events.inserted.connect(self._on_inserted)
        self.events.removed.connect(self._on_removed)

    @property
    def parent(self) -> VedoCanvas:
        return self._parent_ref()

    def _on_inserted(self, i: int, obj: VedoComponent):
        self.parent.vedo_canvas._plt.add(obj._obj).render()
        if len(self) == 1:
            self.parent.vedo_canvas._plt.show()

    def _on_removed(self, i: int, obj: VedoComponent):
        self.parent.vedo_canvas._plt.remove(obj._obj.name).render()


class VedoCanvas(FreeWidget):
    def __init__(self):
        """
        A Visualization toolkit (VTK) canvas for magicclass.

        This widget is useful for visualizing surface and mesh.
        """
        super().__init__()
        self.vedo_canvas = QtVedoCanvas()
        self.set_widget(self.vedo_canvas)
        self._layers = LayerList(parent=self)

    @property
    def layers(self):
        return self._layers

    def screenshot(self) -> np.ndarray:
        """Get screenshot as a numpy array."""
        pic: vedo.Image = self.vedo_canvas._plt.toimage()
        img = pic.tonumpy()
        return img

    @property
    def plotter(self) -> vedo.Plotter:
        return self.vedo_canvas._plt

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
        vol = Volume(volume, _parent=self.vedo_canvas._plt)
        self.layers.append(vol)
        self.vedo_canvas._plt.add(vol._current_obj)
        vol.color = color
        vol.mode = mode
        if len(self.layers) == 1:
            self.vedo_canvas._plt.show(zoom=True)
        return vol

    def add_object(self, *args, object_type: str = None, **kwargs):
        obj = get_object_type(object_type.capitalize())(
            *args, **kwargs, _parent=self.vedo_canvas._plt
        )
        self.layers.append(obj)
        if len(self.layers) == 1:
            self.vedo_canvas._plt.show()
        return obj

    def add_surface(self, data: tuple[np.ndarray, np.ndarray] | tuple[np.ndarray]):
        mesh = Mesh(data, _parent=self.vedo_canvas._plt)
        self.layers.append(mesh)
        if len(self.layers) == 1:
            self.vedo_canvas._plt.show(zoom=True)
        return mesh

    def add_points(
        self,
        data: np.ndarray,
        color=(0.2, 0.2, 0.2),
        alpha=1,
        radius=4,
    ):
        points = Points(
            data,
            color=color,
            alpha=alpha,
            radius=radius,
            _parent=self.vedo_canvas._plt,
        )
        self.layers.append(points)
        if len(self.layers) == 1:
            self.vedo_canvas._plt.show(zoom=True)
        return points

    @property
    def axes(self) -> str:
        """The axes object."""
        return AxesMode(self.vedo_canvas._plt.axes).name

    @axes.setter
    def axes(self, v):
        if self.vedo_canvas._plt.axes_instances:
            current_axes = self.vedo_canvas._plt.axes_instances[0]
        else:
            current_axes = None
        a = getattr(AxesMode, v).value
        try:
            self.vedo_canvas._plt.remove(current_axes)
        except TypeError:
            current_axes.EnabledOff()
        self.vedo_canvas._plt.axes_instances = [None]
        self.vedo_canvas._plt.show(axes=a)
