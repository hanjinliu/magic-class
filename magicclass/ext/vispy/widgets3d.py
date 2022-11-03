from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike
from vispy import scene
from . import layer3d
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
    ) -> layer3d.Image:
        """
        Add a 3D array as a volumic image.

        Parameters
        ----------
        data : ArrayLike
            Image data.
        contrast_limits : tuple[float, float], optional
            Contrast limits of the image.
        rendering : str, optional
            Rendering method.
        iso_threshold : float, optional
            Threshold of iso-surface rendering.
        attenuation : float, optional
            Attenuation of attenuated rendering method.
        cmap : str, optional
            Colormap of image.
        gamma : float, optional
            Gamma value of contrast.
        interpolation : str, optional
            Interpolation method.

        Returns
        -------
        Image
            A new Image layer.
        """
        data = np.asarray(data)
        if data.dtype.kind == "f":
            data = data.astype(np.float32)
        image = layer3d.Image(
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
    ) -> layer3d.IsoSurface:
        """
        Add a 3D array as a iso-surface.

        The difference between this method and the iso-surface rendering of
        ``add_image`` is that the layer created by this method can be a mesh.

        Parameters
        ----------
        data : ArrayLike
            Image data.
        contrast_limits : tuple[float, float], optional
            Contrast limits of the image.
        iso_threshold : float, optional
            Threshold of iso-surface.
        face_color : Color, optional
            Face color of the surface.
        edge_color : Color, optional
            Edge color of the surface.
        shading : str, optional
            Shading mode of the surface.

        Returns
        -------
        Isosurface
            A new Isosurface layer.
        """
        surface = layer3d.IsoSurface(
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
    ) -> layer3d.Surface:
        """
        Add vertices, faces and optional values as a surface.

        Parameters
        ----------
        data : two or three arrays
            Data that defines a surface.
        face_color : Color | None, optional
            Face color of the surface.
        edge_color : Color | None, optional
            Edge color of the surface.
        shading : str, optional
            Shading mode of the surface.

        Returns
        -------
        Surface
            A new Surface layer.
        """
        surface = layer3d.Surface(
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
        color: Color = "white",
        width: float = 1,
        blending: str = "translucent",
    ) -> layer3d.Curve3D:
        """
        Add a (N, 3) array as a curve.

        Parameters
        ----------
        data : ArrayLike
            Coordinates of the curve.
        color : Color, default is "white"
            Color of the curve.
        width : float, default is 1.
            Width of the curve line.
        blending : str, default is "translucent"
            Blending mode of the layer.

        Returns
        -------
        _type_
            _description_
        """
        curve = layer3d.Curve3D(
            data=np.asarray(data, dtype=np.float32),
            viewbox=self._viewbox,
            color=color,
            width=width,
            blending=blending,
        )
        return self.add_layer(curve)

    def add_points(
        self,
        data: ArrayLike,
        face_color: Color = "white",
        edge_color: Color = "white",
        edge_width: float = 0.0,
        size: float = 5.0,
        blending: str = "translucent",
        spherical: bool = True,
    ) -> layer3d.Points3D:
        """
        Add a (N, 3) array as a point cloud.

        Parameters
        ----------
        data : ArrayLike
            Z, Y, X coordinates of the points.
        face_color : Color, optional
            Face color of the points.
        edge_color : Color, optional
            Edge color of the points.
        edge_width : float, default is 0.0
            Edge width of the points.
        size : float, default is 1.0
            Size of the points.
        blending : str, default is "translucent"
            Blending mode of the layer.
        spherical : bool, default is True
            Whether the points are rendered as spherical objects.

        Returns
        -------
        Points3D
            A new Points3D layer.
        """
        points = layer3d.Points3D(
            data=np.asarray(data, dtype=np.float32),
            viewbox=self._viewbox,
            face_color=face_color,
            edge_color=edge_color,
            edge_width=edge_width,
            size=size,
            blending=blending,
            spherical=spherical,
        )
        return self.add_layer(points)

    def add_arrows(
        self,
        data: ArrayLike,
        arrow_type: str = "stealth",
        arrow_size: float = 5.0,
        color: Color ="white",
        width: float = 1.0,
        blending: str = "translucent",
    ) -> layer3d.Arrows3D:
        """
        Add a (N, P, 3) array as a set of arrows.

        ``P`` is the number of points in each arrow. If you want to draw simple
        arrows with lines, the shape of the input array will be (N, 2, 3) and
        ``data[:, 0]`` is the start points and ``data[:, 1]`` is the end points.

        Parameters
        ----------
        data : ArrayLike
            Arrow coordinates.
        arrow_type : str, default is "stealth"
            Shape of the arrow.
        arrow_size : float, default is 5.0
            Size of the arrows.
        color : str, default is "white"
            Color of the arrow and the bodies.
        width : float, default is 1.0
            Width of the arrow bodies.
        blending : str, default is "translucent"
            Blending mode of the layer.

        Returns
        -------
        Arrow3D
            A new Arrow3D layer.
        """
        arrows = layer3d.Arrows3D(
            data=np.asarray(data, dtype=np.float32),
            viewbox=self._viewbox,
            arrow_type=arrow_type,
            arrow_size=arrow_size,
            color=color,
            width=width,
            blending=blending,
        )
        return self.add_layer(arrows)

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
