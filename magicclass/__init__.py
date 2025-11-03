__version__ = "0.7.20"

from magicclass.core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar,
    Parameters,
    build_help,
    get_button,
    get_function_gui,
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
    "widgets",
    "utils",
    "types",
    "functools",
    "logging",
]
