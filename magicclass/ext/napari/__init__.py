from .utils import to_napari
from .widgets import NapariCanvas
from ._magicgui import _register_mgui_types

_register_mgui_types()

del _register_mgui_types

__all__ = ["to_napari", "NapariCanvas"]
