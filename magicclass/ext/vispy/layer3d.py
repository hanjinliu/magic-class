from __future__ import annotations
import numpy as np
from vispy.scene import visuals, ViewBox
from vispy.visuals import (
    VolumeVisual,
    ImageVisual,
    IsosurfaceVisual,
    MeshVisual,
)
from vispy.visuals.filters import WireframeFilter
from ._base import LayerItem

from functools import cached_property
import weakref
from psygnal import SignalGroup, Signal
from magicgui.widgets import ComboBox, FloatSlider, Container
from ...widgets import ColorEdit, FloatRangeSlider


class widget_property(cached_property):
    """Identical to cached_property bug returns a widget."""


class WidgetGroup:
    @widget_property
    def container(self) -> Container:
        widgets = []
        for k, v in self.__class__.__dict__.items():
            if isinstance(v, widget_property) and k != "container":
                widgets.append(v.__get__(self))
        return Container(widgets=widgets, name=f"{self.__class__.__name__}_widget")


class ImageWidgetGroup(WidgetGroup):
    def __init__(self, vol: Image):
        self._layer = weakref.ref(vol)

    @property
    def layer(self) -> Image:
        return self._layer()

    @widget_property
    def rendering(self) -> ComboBox:
        layer = self.layer

        cbox = ComboBox(
            choices=Image.RENDERINGS, value=layer.rendering, name="rendering"
        )
        cbox.changed.connect_setattr(layer, "rendering")

        @layer.events.rendering.connect
        def _(v):
            with cbox.changed.blocked():
                cbox.value = v

        return cbox

    @widget_property
    def contrast_limits(self) -> FloatRangeSlider:
        layer = self.layer
        sl = FloatRangeSlider(
            name="contrast_limits",
            min=layer.data.min(),
            max=layer.data.max(),
            value=layer.contrast_limits,
        )
        sl.changed.connect_setattr(layer, "contrast_limits")

        @layer.events.constrast_limits.connect
        def _(v):
            with sl.changed.blocked():
                sl.value = v

        return sl

    @widget_property
    def iso_threshold(self) -> FloatSlider:
        layer = self.layer
        sl = FloatSlider(
            name="iso_threshold",
            min=layer.data.min(),
            max=layer.data.max(),
            value=self.layer.iso_threshold,
        )
        sl.changed.connect_setattr(self.layer, "iso_threshold")

        @layer.events.iso_threshold.connect
        def _(v):
            with sl.changed.blocked():
                sl.value = v

        return sl

    @widget_property
    def gamma(self) -> FloatSlider:
        layer = self.layer
        sl = FloatSlider(
            name="gamma",
            min=0.0,
            max=1.0,
            value=layer.gamma,
        )
        sl.changed.connect_setattr(self.layer, "gamma")

        @layer.events.gamma.connect
        def _(v):
            with sl.changed.blocked():
                sl.value = v

        return sl

    @widget_property
    def attenuation(self) -> FloatSlider:
        layer = self.layer
        sl = FloatSlider(
            name="attenuation",
            min=0.0,
            max=1.0,
            value=layer.attenuation,
        )
        sl.changed.connect_setattr(self.layer, "attenuation")

        @layer.events.attenuation.connect
        def _(v):
            with sl.changed.blocked():
                sl.value = v

        return sl


class IsoSurfaceWidgetGroup(WidgetGroup):
    def __init__(self, vol: IsoSurface):
        self._layer = weakref.ref(vol)

    @property
    def layer(self) -> IsoSurface:
        return self._layer()

    @widget_property
    def contrast_limits(self) -> FloatRangeSlider:
        layer = self.layer
        sl = FloatRangeSlider(
            name="contrast_limits",
            min=layer.data.min(),
            max=layer.data.max(),
            value=layer.contrast_limits,
        )
        sl.changed.connect_setattr(layer, "contrast_limits")

        @layer.events.constrast_limits.connect
        def _(v):
            with sl.changed.blocked():
                sl.value = v

        return sl

    @widget_property
    def shading(self) -> ComboBox:
        layer = self.layer
        cbox = ComboBox(
            choices=["none", "float", "smooth"], value=layer.shading, name="shading"
        )

        cbox.changed.connect_setattr(layer, "shading")

        @layer.events.shading.connect
        def _(v):
            with cbox.changed.blocked():
                cbox.value = v

        return cbox

    @widget_property
    def iso_threshold(self) -> FloatSlider:
        layer = self.layer
        sl = FloatSlider(
            name="iso_threshold",
            min=layer.data.min(),
            max=layer.data.max(),
            value=self.layer.iso_threshold,
        )
        sl.changed.connect_setattr(self.layer, "iso_threshold")

        @layer.events.iso_threshold.connect
        def _(v):
            with sl.changed.blocked():
                sl.value = v

        return sl

    @widget_property
    def face_color(self) -> ColorEdit:
        layer = self.layer
        col = ColorEdit(
            name="face_color",
            value=layer.face_color,
        )
        col.changed.connect_setattr(layer, "face_color")

        @layer.events.face_color.connect
        def _(v):
            with col.changed.blocked():
                col.value = v

        return col

    @widget_property
    def edge_color(self) -> ColorEdit:
        layer = self.layer
        col = ColorEdit(
            name="edge_color",
            value=layer.edge_color,
        )
        col.changed.connect_setattr(layer, "edge_color")

        @layer.events.edge_color.connect
        def _(v):
            with col.changed.blocked():
                col.value = v

        return col


class ImageSignals(SignalGroup):
    data = Signal(np.ndarray)
    constrast_limits = Signal(tuple[float, float])
    rendering = Signal(str)
    iso_threshold = Signal(float)
    attenuation = Signal(float)
    gamma = Signal(float)
    interpolation = Signal(str)


class Image(LayerItem):
    RENDERINGS = [
        "translucent",
        "mip",
        "minip",
        "attenuated_mip",
        "additive",
        "iso",
        "average",
    ]
    INTERPOLATIONS = ["nearest", "linear"]

    def __init__(
        self,
        data,
        viewbox: ViewBox,
        contrast_limits=None,
        rendering="mip",
        iso_threshold=None,
        attenuation=1.0,
        cmap="grays",
        gamma=1.0,
        interpolation="linear",
    ):
        self.events = ImageSignals()
        self._data = data

        if contrast_limits is None:
            contrast_limits = np.min(self._data), np.max(self._data)

        self._contrast_limits = contrast_limits
        self._rendering = rendering
        self._iso_threshold = iso_threshold
        self._attenuation = attenuation
        self._cmap = cmap
        self._gamma = gamma
        self._interpolation = interpolation

        self._viewbox = viewbox
        self._visual: VolumeVisual | ImageVisual = None
        self._create_visual(self._data, self._interpolation)
        self.events.data.connect(self._on_data_change)
        self.events.constrast_limits.connect(self._on_constrast_limits_change)
        self.events.iso_threshold.connect(self._on_iso_threshold_change)
        self.events.rendering.connect(self._on_rendering_change)
        self.events.gamma.connect(self._on_gamma_change)
        self.events.attenuation.connect(self._on_attenuation_change)
        self.events.interpolation.connect(self._on_interpolation_change)

        self.widgets = ImageWidgetGroup(self)

    def _create_visual(self, data: np.ndarray, interpolation: str | None = None):
        if data.ndim == 2:
            if interpolation is None:
                interpolation = "nearest"
            self._visual = visuals.Image(
                data,
                clim=self._contrast_limits,
                method="auto",
                cmap=self._cmap,
                gamma=self._gamma,
                interpolation=interpolation,
                parent=self._viewbox.scene,
            )

        elif data.ndim == 3:
            if interpolation is None:
                interpolation = "linear"
            self._visual = visuals.Volume(
                data,
                clim=self._contrast_limits,
                method=self._rendering,
                threshold=self._iso_threshold,
                attenuation=self._attenuation,
                cmap=self._cmap,
                gamma=self._gamma,
                interpolation=interpolation,
                parent=self._viewbox.scene,
            )
        else:
            raise ValueError("Only 2D and 3D images are supported.")

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        self.events.data.emit(value)

    def _on_data_change(self, value):
        value = np.asarray(value)
        if self._visual is None or value.ndim != self._data.ndim:
            self._visual.parent = None
            del self._visual
            self._create_visual(value, None)
        else:
            self._visual.set_data(value)
        self._data = value
        self._visual.update()

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, value) -> None:
        min, max = value
        if min > max:
            raise ValueError("min > max.")
        self.events.constrast_limits.emit(value)

    def _on_constrast_limits_change(self, value):
        self._visual.clim = value
        self._contrast_limits = value
        self._visual.update()

    @property
    def rendering(self) -> str:
        return self._rendering

    @rendering.setter
    def rendering(self, value: str) -> None:
        if not value in self.__class__.RENDERINGS:
            raise ValueError(f"'rendering' must be in {self.__class__.RENDERINGS}.")
        self.events.rendering.emit(value)

    def _on_rendering_change(self, value):
        self._visual.method = value
        self._rendering = value
        self._visual.update()

    @property
    def iso_threshold(self) -> float:
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, value) -> None:
        self.events.iso_threshold.emit(float(value))

    def _on_iso_threshold_change(self, value):
        self._iso_threshold = value
        self._visual.threshold = self._iso_threshold
        self._visual.update()

    @property
    def gamma(self) -> float:
        return self._gamma

    @gamma.setter
    def gamma(self, value) -> None:
        self.events.gamma.emit(float(value))

    def _on_gamma_change(self, value):
        self._gamma = value
        self._visual.gamma = self._gamma
        self._visual.update()

    @property
    def attenuation(self) -> float:
        return self._attenuation

    @attenuation.setter
    def attenuation(self, value) -> None:
        self.events.attenuation.emit(float(value))

    def _on_attenuation_change(self, value):
        self._attenuation = value
        self._visual.attenuation = self._attenuation
        self._visual.update()

    @property
    def interpolation(self) -> float:
        return self._interpolation

    @interpolation.setter
    def interpolation(self, value) -> None:
        self.events.interpolation.emit(value)

    def _on_interpolation_change(self, value):
        self._interpolation = value
        self._visual.interpolation = self._interpolation
        self._visual.update()


class _SurfaceBase(LayerItem):
    _visual: visuals.Mesh | visuals.Isosurface
    _wireframe: WireframeFilter

    def __init__(
        self,
        data,
        viewbox: ViewBox,
        face_color=None,
        edge_color=None,
        shading="none",
    ):
        self._viewbox = viewbox
        self._create_visual(data)
        self._wireframe = WireframeFilter()
        self._visual.attach(self._wireframe)
        self._data = data

        if edge_color is None:
            edge_color = [0.7, 0.7, 0.7, 1.0]
        self.edge_color = edge_color

        if face_color is None:
            face_color = [0.7, 0.7, 0.7, 1.0]
        self.face_color = face_color

        self.shading = shading

    def _create_visual(self, data):
        raise NotImplementedError()

    @property
    def face_color(self) -> np.ndarray:
        return self._visual.color.rgba

    @face_color.setter
    def face_color(self, color):
        self._face_color = color
        self.events.face_color.emit(color)

    def _on_face_color_change(self, color):
        self._visual.color = color

    @property
    def edge_color(self) -> np.ndarray:
        return self._wireframe.color.rgba

    @edge_color.setter
    def edge_color(self, color) -> None:
        self.events.edge_color.emit(color)

    def _on_edge_color_change(self, color):
        self._wireframe.color = color
        self._visual.update()

    color = property(fget=None)

    @color.setter
    def color(self, color):
        self.face_color = color
        self.edge_color = color

    @property
    def shading(self) -> str:
        """Return current shading mode of the layer."""
        return self._visual.shading or "none"

    @shading.setter
    def shading(self, v):
        self.events.shading.emit(v)

    def _on_shading_change(self, v):
        if v == "none":
            v = None
        self._visual._shading = v


class IsoSurfaceSignals(SignalGroup):
    data = Signal(np.ndarray)
    constrast_limits = Signal(tuple[float, float])
    iso_threshold = Signal(float)
    shading = Signal(str)
    face_color = Signal(tuple)
    edge_color = Signal(tuple)


class IsoSurface(_SurfaceBase):
    def __init__(
        self,
        data,
        viewbox: ViewBox,
        contrast_limits=None,
        iso_threshold=None,
        face_color=None,
        edge_color=None,
        shading="smooth",
    ):
        self.events = IsoSurfaceSignals()
        data = np.asarray(data)
        data = data.transpose(list(range(data.ndim))[::-1])

        if contrast_limits is None:
            contrast_limits = np.min(data), np.max(data)

        self._contrast_limits = contrast_limits

        if iso_threshold is None:
            c0, c1 = self._contrast_limits
            iso_threshold = (c0 + c1) / 2

        self._iso_threshold = iso_threshold
        super().__init__(
            data,
            viewbox=viewbox,
            face_color=face_color,
            edge_color=edge_color,
            shading=shading,
        )
        self.events.data.connect(self._on_data_change)
        self.events.constrast_limits.connect(self._on_contrast_limits_change)
        self.events.shading.connect(self._on_shading_change)
        self.events.iso_threshold.connect(self._on_iso_threshold_change)
        self.events.face_color.connect(self._on_face_color_change)
        self.events.edge_color.connect(self._on_edge_color_change)
        self.widgets = IsoSurfaceWidgetGroup(self)

    def _create_visual(self, data):
        self._visual: IsosurfaceVisual = visuals.Isosurface(
            data, level=self.iso_threshold, parent=self._viewbox.scene
        )
        return None

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        value = np.asarray(value)
        self.events.data.emit(value)

    def _on_data_change(self, value):
        self._visual.set_data(value)
        self._data = value
        self._visual.update()

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, value) -> None:
        self.events.constrast_limits.emit(value)

    def _on_contrast_limits_change(self, value):
        self._visual.clim = value
        self._contrast_limits = value
        self._visual.update()

    @property
    def iso_threshold(self) -> float:
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, value) -> None:
        self.events.iso_threshold.emit(float(value))

    def _on_iso_threshold_change(self, value):
        self._iso_threshold = value
        self._visual.level = self._iso_threshold
        self._visual.update()


class Surface(_SurfaceBase):
    def _create_visual(self, data):
        self._visual: MeshVisual = visuals.Mesh(
            vertices=data[0], faces=data[1], parent=self._viewbox.scene
        )
        self.data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value) -> None:
        if len(value) == 2:
            verts, faces = value
            vals = None
        elif len(value) == 3:
            verts, faces, vals = value
        else:
            raise ValueError("Data must be vertices, faces (, values).")
        self._visual.set_data(vertices=verts, faces=faces, vertex_values=vals)
        self._data = (verts, faces, vals)
        self._visual.update()

    @property
    def face_color(self) -> np.ndarray:
        return self._visual.color

    @face_color.setter
    def face_color(self, color) -> None:
        verts, faces, vals = self._data
        self._visual.set_data(
            vertices=verts, faces=faces, vertex_values=vals, color=color
        )
        self._visual.update()
