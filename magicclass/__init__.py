__version__ = "0.5.9"

from .core import magicclass, magicmenu, magiccontext, WidgetType, Parameters, Bound, MagicTemplate
from .wrappers import set_options, click, set_design, do_not_record
from .fields import field, vfield
from ._base import wraps, defaults
from . import widgets

from magicgui import *