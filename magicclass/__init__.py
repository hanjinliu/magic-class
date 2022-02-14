__version__ = "0.5.21.dev0"

from .core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar,
    Parameters,
    build_help,
)

from .wrappers import (
    set_options,
    click,
    set_design,
    do_not_record,
    bind_key,
    confirm,
    nogui,
)

from .fields import field, vfield
from .gui._base import wraps, defaults, MagicTemplate, PopUpMode
from ._typing import WidgetType, Bound, Color
from .gui.keybinding import Key
from . import widgets, utils

from magicgui import *
