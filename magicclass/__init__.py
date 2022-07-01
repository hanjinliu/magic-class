__version__ = "0.6.7.dev1"

from .core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar,
    Parameters,
    build_help,
    get_function_gui,
    redo,
    update_widget_state,
)

from .wrappers import (
    set_options,
    set_design,
    do_not_record,
    bind_key,
    confirm,
    nogui,
    mark_preview,
)

from .fields import field, vfield, widget_property, FieldGroup, HasFields
from ._gui._base import wraps, defaults, MagicTemplate, PopUpMode
from ._gui.keybinding import Key
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
    "update_widget",
    "set_options",
    "set_design",
    "do_not_record",
    "bind_key",
    "confirm",
    "nogui",
    "mark_preview",
    "field",
    "vfield",
    "widget_property",
    "FieldGroup",
    "HasFields",
    "wraps",
    "defaults",
    "MagicTemplate",
    "PopUpMode",
    "Key",
]


def __getattr__(key: str):
    if key == "click":
        import warnings

        warnings.warn(
            "Function click is moving to magicclass.utils and will be deleted from "
            "magicclass namespace. Please 'from magicclass.utils import click'.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .utils import click

        return click
    raise AttributeError(f"module {__name__!r} has no attribute {key!r}")
