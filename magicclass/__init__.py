__version__ = "0.7.13"

from magicclass.core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar,
    Parameters,
    build_help,
    get_button,
    get_function_gui,
    repeat,
    update_widget_state,
)

from magicclass.wrappers import (
    set_options,
    set_design,
    do_not_record,
    bind_key,
    confirm,
    nogui,
    impl_preview,
    setup_function_gui,
    mark_on_calling,
    mark_on_called,
    abstractapi,
)

from magicclass.fields import (
    field,
    vfield,
    widget_property,
    magicproperty,
    FieldGroup,
    HasFields,
)
from magicclass._gui._base import defaults, MagicTemplate, PopUpMode
from magicclass._gui._icon import Icon
from magicclass import widgets, utils, types, functools, logging

from magicgui import *  # noqa: F403

__all__ = [
    "magicclass",
    "magicmenu",
    "magiccontext",
    "magictoolbar",
    "Parameters",
    "build_help",
    "get_button",
    "get_function_gui",
    "repeat",
    "update_widget_state",
    "set_options",
    "set_design",
    "do_not_record",
    "bind_key",
    "confirm",
    "nogui",
    "impl_preview",
    "setup_function_gui",
    "mark_on_calling",
    "mark_on_called",
    "abstractapi",
    "field",
    "vfield",
    "widget_property",
    "magicproperty",
    "FieldGroup",
    "HasFields",
    "defaults",
    "MagicTemplate",
    "PopUpMode",
    "Icon",
    "widgets",
    "utils",
    "types",
    "functools",
    "logging",
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

    elif key == "dataclass_gui":
        warnings.warn(
            "Function `dataclass_gui` is deprecated. `magicgui`'s `guiclass` "
            "does almost the same thing. Please use `guiclass` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from magicclass.fields import dataclass_gui

        return dataclass_gui

    elif key == "Key":
        warnings.warn(
            "Enum `Key` is deprecated. Use string directly for `bind_key`.",
            DeprecationWarning,
            stacklevel=2,
        )
        from ._gui.keybinding import Key

        return Key

    elif key == "mark_preview":
        warnings.warn(
            "Function `mark_preview` is deprecated. Use `impl_preview` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .wrappers import impl_preview

        return impl_preview

    raise AttributeError(f"module {__name__!r} has no attribute {key!r}")
