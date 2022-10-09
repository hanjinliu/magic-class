from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike
from vispy import scene
from .layer3d import Image, IsoSurface, Surface, Curve3D
from .layerlist import LayerList
from ._base import SceneCanvas, HasViewBox, MultiPlot, LayerItem
from .camera import Camera

from ...widgets import FreeWidget
from ...types import Color


class Has3DViewBox(HasViewBox):
    """
    A Vispy canvas for 3-D object visualization.

    Very similar to napari. This widget can be used independent of napari, or
    as a mini-viewer of napari.
    """

    def __init__(self, viewbox: scene.ViewBox):
        super().__init__(viewbox)
        self._camera = Camera(viewbox)

    @property
    def layers(self):
        """Return the layer list."""
        return self._layerlist

    @property
    def camera(self) -> Camera:
        """Return the native camera."""
        return self._camera

    def add_image(
        self,
        data: ArrayLike,
        *,
        contrast_limits: tuple[float, float] = None,
        rendering: str = "mip",
        iso_threshold: float | None = None,
        attenuation: float = 1.0,
        cmap: str = "grays",
        gamma: float = 1.0,
        interpolation: str = "linear",
    ):
        image = Image(
            data,
            self._viewbox,
            contrast_limits=contrast_limits,
            rendering=rendering,
            iso_threshold=iso_threshold,
            attenuation=attenuation,
            cmap=cmap,
            gamma=gamma,
            interpolation=interpolation,
        )

        return self.add_layer(image)

    def add_isosurface(
        self,
        data: ArrayLike,
        *,
        contrast_limits: tuple[float, float] | None = None,
        iso_threshold: float | None = None,
        face_color: Color | None = None,
        edge_color: Color | None = None,
        shading: str = "smooth",
    ):
        surface = IsoSurface(
            data,
            self._viewbox,
            contrast_limits=contrast_limits,
            iso_threshold=iso_threshold,
            edge_color=edge_color,
            face_color=face_color,
            shading=shading,
        )

        return self.add_layer(surface)

    def add_surface(
        self,
        data: tuple[ArrayLike, ArrayLike] | tuple[ArrayLike, ArrayLike, ArrayLike],
        *,
        face_color: Color | None = None,
        edge_color: Color | None = None,
        shading: str = "smooth",
    ):
        surface = Surface(
            data,
            self._viewbox,
            face_color=face_color,
            edge_color=edge_color,
            shading=shading,
        )
        return self.add_layer(surface)

    def add_curve(
        self,
        data: ArrayLike,
        color="white",
        width=1,
    ):
        curve = Curve3D(
            data=np.asarray(data, dtype=np.float32),
            viewbox=self._viewbox,
            color=color,
            width=width,
        )
        return self.add_layer(curve)

    def add_layer(self, layer: LayerItem):
        """Add a layer item to the canvas."""
        self.layers.append(layer)
        if len(self.layers) == 1:
            low, high = layer._get_bbox()
            self.camera.scale = max(high - low)
            self.camera.center = (high + low) / 2
            self.camera.angles = (0.0, 0.0, 90.0)

        self._viewbox.update()
        return layer


class Vispy3DCanvas(FreeWidget, Has3DViewBox):
    """A Vispy based 3-D canvas."""

    def __init__(self):
        super().__init__()
        self._scene = SceneCanvas()
        grid = self._scene.central_widget.add_grid()
        _viewbox = grid.add_view()
        Has3DViewBox.__init__(self, _viewbox)
        self._layerlist = LayerList()
        self._scene.create_native()
        self.set_widget(self._scene.native)


class VispyMulti3DCanvas(MultiPlot):
    """A multiple Vispy based 3-D canvas."""

    _base_class = Has3DViewBox

    # BUG: the second canvas has wrong offset. Need updates in event object?
