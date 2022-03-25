from enum import Enum


class Rendering(Enum):
    """Rendering mode suppored in vtk."""

    composite = 0
    mip = 1
    minip = 2
    average = 3
    additive = 4


class Mode(Enum):
    volume = "volume"
    iso = "iso"
    lego = "lego"
    mesh = "mesh"
    wireframe = "wireframe"


class AxesMode(Enum):
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
