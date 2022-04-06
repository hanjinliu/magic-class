__version__ = "0.6.2"

from .core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar,
    Parameters,
    build_help,
    get_function_gui,
    redo,
)

from .wrappers import (
    set_options,
    click,
    set_design,
    do_not_record,
    bind_key,
    confirm,
    nogui,
    mark_preview,
)

from .fields import field, vfield
from .gui._base import wraps, defaults, MagicTemplate, PopUpMode
from .gui.keybinding import Key
from . import widgets, utils, types

from magicgui import *

__all__ = [
    "magicclass",
    "magicmenu",
    "magiccontext",
    "magictoolbar",
    "Parameters",
    "build_help",
    "get_function_gui",
    "redo",
    "set_options",
    "click",
    "set_design",
    "do_not_record",
    "bind_key",
    "confirm",
    "nogui",
    "mark_preview",
    "field",
    "vfield",
    "wraps",
    "defaults",
    "MagicTemplate",
    "PopUpMode",
    "Key",
]


def __getattr__(name):
    if name in ("WidgetType", "Bound", "Color", "Optional"):
        import warnings
        from . import types

        warnings.warn(
            f"{name} should be imported from 'magicclass.types'. This will raise "
            "error in future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(types, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
