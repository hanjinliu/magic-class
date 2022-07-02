__version__ = "0.6.7.dev2"

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
from ._gui._icon import Icon
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
    "update_widget_state",
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
    "Icon",
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
