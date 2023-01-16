__version__ = "0.6.14.dev0"

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
    impl_preview,
    mark_on_calling,
    mark_on_called,
    abstractapi,
)

from .fields import (
    field,
    vfield,
    widget_property,
    magicproperty,
    FieldGroup,
    HasFields,
    dataclass_gui,
)
from ._gui._base import defaults, MagicTemplate, PopUpMode
from ._gui.keybinding import Key
from ._gui._icon import Icon
from . import widgets, utils, types, functools, logging

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
    "impl_preview",
    "mark_on_calling",
    "mark_on_called",
    "abstractapi",
    "field",
    "vfield",
    "widget_property",
    "magicproperty",
    "FieldGroup",
    "HasFields",
    "dataclass_gui",
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

    elif key == "wraps":
        warnings.warn(
            "Function `wraps` is moved to magicclass.functools. Please use "
            "`from magicclass.functools import wraps` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from magicclass.functools import wraps

        return wraps

    raise AttributeError(f"module {__name__!r} has no attribute {key!r}")
