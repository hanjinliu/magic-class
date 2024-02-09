from __future__ import annotations
from typing import Callable, Generic, TypeVar, overload
import weakref
import vedo
from .const import Representation
from magicclass.fields import vfield, HasFields
from magicclass.types import Color

_VedoType = TypeVar("_VedoType", bound=vedo.CommonAlgorithms)


class VedoComponent(HasFields):
    _vedo_type: type[_VedoType] | Callable[..., _VedoType]

    def __init__(
        self, *args, _parent: vedo.Plotter = None, _emit: bool = True, **kwargs
    ):
        if self._vedo_type is None:
            raise TypeError("Base vedo type is unknown.")
        self._obj = self._vedo_type(*args, **kwargs)
        self._parent_ref = weakref.ref(_parent)
        if _emit:
            self.widgets.emit_all()

    @overload
    def __init_subclass__(cls, base: type[_VedoType] = None) -> None:  # noqa
        ...

    @overload
    def __init_subclass__(cls, base: Callable[..., _VedoType] = None) -> None:  # noqa
        ...

    def __init_subclass__(cls, base=None) -> None:
        cls._vedo_type = base

    visible = vfield(True, name="visibility")

    @visible.connect
    def _on_visible_change(self, v: bool):
        if v:
            self._obj.on()
        else:
            self._obj.off()
        self._update()

    def _update(self):
        self._parent_ref().qt_widget.Render()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{hex(id(self))}>"


class Points(VedoComponent, base=vedo.Points):
    _obj: vedo.Points
    color = vfield(Color)
    size = vfield(float)
    spherical = vfield(False)
    scale = vfield(float)

    def __init__(
        self,
        data,
        color=(0.2, 0.2, 0.2),
        alpha=1,
        radius=4,
        _parent: vedo.Plotter = None,
        _emit: bool = True,
    ):
        super().__init__(
            data, c=color, alpha=alpha, r=radius, _parent=_parent, _emit=_emit
        )

    @color.connect
    def _on_color_change(self, v):
        self._obj.color(v[:3])
        self._update()

    @size.connect
    def _on_size_change(self, v):
        self._obj.point_size(v)
        self._update()

    @spherical.connect
    def _on_spherical_change(self, v):
        self._obj.render_points_as_spheres(v)
        self._update()

    @scale.connect
    def _on_scale_change(self, v):
        self._obj.scale(v, reset=True)
        self._update()


class Mesh(VedoComponent, base=vedo.Mesh):
    _obj: vedo.Mesh

    color = vfield(Color)
    occlusion = vfield(0.0)
    scale = vfield(1.0)
    representation = vfield(Representation.surface)
    linewidth = vfield(0.0, options={"min": 0.0, "max": 10})
    backface_color = vfield(Color)
    frontface_culling = vfield(False)
    backface_culling = vfield(False)
    lines_as_tubes = vfield(False)

    @color.connect
    def _on_color_change(self, v):
        self._obj.color([v * 255 for v in v[:3]])
        self._update()

    @scale.connect
    def _on_scale_change(self, v):
        self._obj.scale(v, reset=True)
        self._update()

    @representation.connect
    def _on_representation_change(self, v: Representation) -> None:
        self._obj.property.SetRepresentation(v.value)
        self._update()

    @linewidth.connect
    def _on_linewidth_change(self, v):
        self._obj.linewidth(v)
        self._update()

    @backface_color.connect
    def _on_backface_color_change(self, v):
        self._obj.backcolor([v * 255 for v in v[:3]])
        self._update()

    @frontface_culling.connect
    def _on_frontface_culling_change(self, v):
        self._obj.frontface_culling(v)
        self._update()

    @backface_culling.connect
    def _on_backface_culling_change(self, v):
        self._obj.backface_culling(v)
        self._update()

    @lines_as_tubes.connect
    def _on_lines_as_tubes_change(self, v):
        self._obj.render_lines_as_tubes(v)
        self._update()


# fmt: off
class Path(Mesh, base=vedo.Line): ...
class Sphere(Mesh, base=vedo.Sphere): ...
class Spheres(Mesh, base=vedo.Spheres): ...
class Spline(Mesh, base=vedo.Spline): ...
class KSpline(Mesh, base=vedo.KSpline): ...
class CSpline(Mesh, base=vedo.CSpline): ...
class Tube(Mesh, base=vedo.Tube): ...
class Ribbon(Mesh, base=vedo.Ribbon): ...
class Arrow(Mesh, base=vedo.Arrow): ...
class Arrows(Mesh, base=vedo.Arrows): ...
class Circle(Mesh, base=vedo.Circle): ...
class Disc(Mesh, base=vedo.Disc): ...
class Earth(Mesh, base=vedo.Earth): ...
class Ellipsoid(Mesh, base=vedo.Ellipsoid): ...
class Box(Mesh, base=vedo.Box): ...
class Cube(Mesh, base=vedo.Cube): ...
class Spring(Mesh, base=vedo.Spring): ...
class Cylinder(Mesh, base=vedo.Cylinder): ...
class Cone(Mesh, base=vedo.Cone): ...
class Text(Mesh, base=vedo.Text3D): ...
# fmt: on


def get_object_type(name: str) -> type[VedoComponent]:
    t = globals().get(name, None)
    if not isinstance(t, (type, Generic)):
        raise ValueError(f"Object type {t} not found.")
    return t
