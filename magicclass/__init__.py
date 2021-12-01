__version__ = "0.5.10"

from .core import magicclass, magicmenu, magiccontext, WidgetType, Parameters, Bound, MagicTemplate
from .wrappers import set_options, click, set_design, do_not_record, bind_key
from .fields import field, vfield
from .gui._base import wraps, defaults
from .gui.keybinding import Key
from . import widgets, utils

from magicgui import *