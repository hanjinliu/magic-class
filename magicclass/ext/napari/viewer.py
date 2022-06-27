from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from napari.components.viewer_model import ViewerModel
from napari.qt import QtViewer

from ...widgets import FreeWidget

if TYPE_CHECKING:
    from napari import layers as nl


class QtLayerWidget(QtW.QSplitter):
    def __init__(self, parent: QtViewerWidget):
        super().__init__(Qt.Orientation.Vertical, parent)
        layercontrol = parent._qt_viewer.dockLayerControls.widget()
        self.addWidget(layercontrol)
        layerlist = parent._qt_viewer.dockLayerList.widget()
        self.addWidget(layerlist)


class QtViewerWidget(QtW.QSplitter):
    def __init__(self):
        super().__init__()
        self._viewer_model = ViewerModel(title="Model")
        self._qt_viewer = QtViewer(self._viewer_model)
        self._layer_widget = QtLayerWidget(self)
        self.addWidget(self._layer_widget)
        self.addWidget(self._qt_viewer)


class ViewerWidget(FreeWidget):
    def __init__(self):
        super().__init__()
        self._qtwidget = QtViewerWidget()
        self.set_widget(self._qtwidget)

    @property
    def layers(self):
        return self._qtwidget._viewer_model.layers

    @property
    def dims(self):
        return self._qtwidget._viewer_model.dims

    @property
    def axes(self):
        return self._qtwidget._viewer_model.axes

    @property
    def camera(self):
        return self._qtwidget._viewer_model.camera

    @property
    def cursor(self):
        return self._qtwidget._viewer_model.cursor

    @property
    def grid(self):
        return self._qtwidget._viewer_model.grid

    @property
    def scale_bar(self):
        return self._qtwidget._viewer_model.scale_bar

    @property
    def text_overlay(self):
        return self._qtwidget._viewer_model.text_overlay

    @property
    def cursor(self):
        return self._qtwidget._viewer_model.cursor

    def add_image(self, *args, **kwargs) -> nl.Image:
        return self._qtwidget._viewer_model.add_image(*args, **kwargs)

    def add_shapes(self, *args, **kwargs) -> nl.Shapes:
        return self._qtwidget._viewer_model.add_shapes(*args, **kwargs)

    def add_points(self, *args, **kwargs) -> nl.Points:
        return self._qtwidget._viewer_model.add_points(*args, **kwargs)

    def add_vectors(self, *args, **kwargs) -> nl.Vectors:
        return self._qtwidget._viewer_model.add_vectors(*args, **kwargs)

    def add_labels(self, *args, **kwargs) -> nl.Labels:
        return self._qtwidget._viewer_model.add_labels(*args, **kwargs)

    def add_surface(self, *args, **kwargs) -> nl.Surface:
        return self._qtwidget._viewer_model.add_surface(*args, **kwargs)

    def add_tracks(self, *args, **kwargs) -> nl.Tracks:
        return self._qtwidget._viewer_model.add_tracks(*args, **kwargs)
