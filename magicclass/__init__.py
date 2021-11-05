__version__ = "0.5.4dev2"

from .core import magicclass, magicmenu, magiccontext, WidgetType, Parameters
from .wrappers import set_options, click, set_design, do_not_record
from .field import field
from ._base import wraps, defaults
from . import widgets