__version__ = "0.5.23.dev1"

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
from .types import WidgetType, Bound, Color, Optional
from .gui.keybinding import Key
from . import widgets, utils

from magicgui import *
