__version__ = "0.6.11.dev0"

from .core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar,
    Parameters,
    build_help,
    get_function_gui,
    repeat,
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

from .fields import field, vfield, widget_property, FieldGroup, HasFields, dataclass_gui
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
    "repeat",
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
    "dataclass_gui",
    "wraps",
    "defaults",
    "MagicTemplate",
    "PopUpMode",
    "Key",
    "Icon",
]


def __getattr__(key: str):
    import warnings

    if key == "click":
        warnings.warn(
            "Function `click` is moving to magicclass.utils and will be deleted from "
            "magicclass namespace. Please 'from magicclass.utils import click'.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .utils import click

        return click
    elif key == "redo":
        warnings.warn(
            "Function `redo` is deprecated because its name is confusing. Please "
            "use `repeat` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .core import repeat

        return repeat

    raise AttributeError(f"module {__name__!r} has no attribute {key!r}")
