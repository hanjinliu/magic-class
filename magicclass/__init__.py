__version__ = "0.5.19"

from .core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar, 
    Parameters,
    Bound,
    build_help
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
from ._typing import WidgetType
from .gui.keybinding import Key
from . import widgets, utils

from magicgui import *