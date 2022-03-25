from enum import Enum


class Rendering(Enum):
    """Rendering mode suppored in vtk."""

    composite = "composite"
    mip = "mip"
    minip = "minip"
    average = "average"
    additive = "additive"

    def toint(self) -> int:
        return _RENDERING_DICT[self]


_RENDERING_DICT = {
    Rendering.composite: 0,
    Rendering.mip: 1,
    Rendering.minip: 2,
    Rendering.average: 3,
    Rendering.additive: 4,
}


class Mode(Enum):
    volume = "volume"
    iso = "iso"
    lego = "lego"
    mesh = "mesh"


class AxesMode(Enum):
    none = "none"
    wall = "wall"
    cartesian = "cartesian"
    cartesian_positive = "cartesian_positive"
    triad = "triad"
    cube = "cube"
    corner = "corner"
    ruler = "ruler"
    cubeaxesactor = "cubeaxesactor"
    box = "box"
    circle = "circle"
    grid = "grid"
    polar = "polar"
    ruler_simple = "ruler_simple"

    def toint(self) -> int:
        return _AXES_MODE_DICT[self]


_AXES_MODE_DICT = {
    AxesMode.none: 0,
    AxesMode.wall: 1,
    AxesMode.cartesian: 2,
    AxesMode.cartesian_positive: 3,
    AxesMode.triad: 4,
    AxesMode.cube: 5,
    AxesMode.corner: 6,
    AxesMode.ruler: 7,
    AxesMode.cubeaxesactor: 8,
    AxesMode.box: 9,
    AxesMode.circle: 10,
    AxesMode.grid: 11,
    AxesMode.polar: 12,
    AxesMode.ruler_simple: 13,
}
