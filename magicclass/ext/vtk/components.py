from __future__ import annotations
from typing import Callable, Generic, Sequence, TypeVar, overload
from typing_extensions import ParamSpec
import weakref
import vedo
import numpy as np
from .const import Representation

_VtkType = TypeVar("_VtkType", bound=vedo.BaseActor)
_P = ParamSpec("_P")


class VtkComponent:
    _vtk_type: type[_VtkType] | Callable[_P, _VtkType]

    def __init__(self, *args, _parent: vedo.Plotter = None, **kwargs):
        if self._vtk_type is None:
            raise TypeError("Base VTK type is unknown.")
        self._obj = self._vtk_type(*args, **kwargs)
        self._visible = True
        self._parent_ref = weakref.ref(_parent)

        self._set_properties()

    def _set_properties(self):
        pass

    @overload
    def __init_subclass__(cls, base: _VtkType = None) -> None:  # noqa
        ...

    @overload
    def __init_subclass__(cls, base: Callable[_P, _VtkType] = None) -> None:  # noqa
        ...

    def __init_subclass__(cls, base=None) -> None:
        cls._vtk_type = base

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, v):
        v = bool(v)
        if v:
            self._obj.on()
        else:
            self._obj.off()
        self._visible = v
        self._update()

    def _update(self):
        self._parent_ref().window.Render()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{hex(id(self))}>"


_L = TypeVar("_L", bound="Points")
_V = TypeVar("_V")


class VtkProperty(property, Generic[_L, _V]):
    def __init__(
        self,
        vedo_fname: str | None = None,
        vtk_fname: str | None = None,
        converter: type | None = None,
        doc: str | None = None,
        **kwargs,
    ):
        if converter is None:
            converter = lambda x: x
        self._converter = converter

        if vedo_fname is not None:
            fget, fset = self._from_vedo(vedo_fname, **kwargs)
        else:
            fget, fset = self._from_vtk(f"Get{vtk_fname}", f"Set{vtk_fname}", **kwargs)

        super().__init__(fget, fset, doc=doc)

    def _from_vedo(self, vedo_fname: str, **kwargs):
        # getter function
        def fget(x: _L) -> _V:
            return self._converter(getattr(x._obj, vedo_fname)())

        # setter function
        def fset(x: _L, value: _V) -> None:
            getattr(x._obj, vedo_fname)(self._converter(value), **kwargs)
            x._update()

        return fget, fset

    def _from_vtk(self, fget_name: str, fset_name: str, **kwargs):
        # getter function
        def fget(x: _L) -> _V:
            return self._converter(getattr(x._obj.property, fget_name)())

        # setter function
        def fset(x: _L, value: _V) -> None:
            getattr(x._obj.property, fset_name)(self._converter(value), **kwargs)
            x._update()

        return fget, fset


class Points(VtkComponent, base=vedo.Points):
    # fmt: off
    color: VtkProperty[Points, np.ndarray] = VtkProperty("color", doc="Point color.")  # noqa
    point_size: VtkProperty[Points, float] = VtkProperty(vtk_fname="PointSize", converter=float, doc="Size of points.")  # noqa
    spherical: VtkProperty[Points, float] = VtkProperty(vtk_fname="RenderPointsAsSpheres", converter=float, doc="Render points to look spherical")  # noqa
    occlusion: VtkProperty[Points, float] = VtkProperty("occlusion", doc="Occlusion strength.")  # noqa
    pos: VtkProperty[Points, Sequence[float]] = VtkProperty("pos", doc="position the points.")  # noqa
    scale: VtkProperty[Points, float] = VtkProperty("scale", absolute=True, doc="scale of the layer.")  # noqa
    # fmt: on


class Mesh(Points, base=vedo.Mesh):
    def _set_properties(self):
        super()._set_properties()
        self._representation = Representation.surface

    # fmt: off
    linewidth: VtkProperty[Mesh, float] = VtkProperty("lineWidth", doc="Line width of edges.")  # noqa
    backface_color: VtkProperty[Mesh, np.ndarray] = VtkProperty("backColor", doc="Color of the backside of polygons.")  # noqa
    frontface_culling: VtkProperty[Points, bool] = VtkProperty(vtk_fname="FrontfaceCulling", converter=bool, doc="Culling of front face.")  # noqa
    backface_culling: VtkProperty[Points, bool] = VtkProperty(vtk_fname="BackfaceCulling", converter=bool, doc="Culling of back face.")  # noqa
    lines_as_tubes: VtkProperty[Points, bool] = VtkProperty(vtk_fname="RenderLinesAsTubes", converter=bool, doc="Render mesh lines as tubes.")  # noqa
    # fmt: on

    @property
    def representation(self) -> Representation:
        """
        Representation mode of mesh.

        One of "points", "wireframe", "surface".
        """
        return self._representation.name

    @representation.setter
    def representation(self, value) -> None:
        rep: Representation = getattr(Representation, value)
        self._obj.property.SetRepresentation(rep.value)
        self._representation = rep
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


def get_object_type(name: str) -> type[VtkComponent]:
    t = globals().get(name, None)
    if not isinstance(t, (type, Generic)):
        raise ValueError(f"Object type {t} not found.")
    elif not issubclass(t, VtkComponent):
        raise ValueError(f"Object type {t} not found.")
    return t
