from enum import Enum


class StringEnum(Enum):
    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __str__(self) -> str:
        return self.name


class Rendering(StringEnum):
    """Volume rendering mode suppored in vtk."""

    composite = 0
    mip = 1
    minip = 2
    average = 3
    additive = 4


class Mode(StringEnum):
    volume = "volume"
    iso = "iso"
    lego = "lego"
    mesh = "mesh"
    wireframe = "wireframe"


class Representation(StringEnum):
    points = 0
    wireframe = 1
    surface = 2

    def __int__(self):
        return self.value


class AxesMode(StringEnum):
    none = 0
    wall = 1
    cartesian = 2
    cartesian_pos = 3
    triad = 4
    cube = 5
    corner = 6
    ruler = 7
    ruler_axes = 8
    box = 9
    circle = 10
    grid = 11
    polar = 12
    ruler1d = 13
