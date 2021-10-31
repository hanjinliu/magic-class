__version__ = "0.5.3dev0"

from .core import magicclass, magicmenu, magiccontext, WidgetType
from .wrappers import set_options, click, set_design
from .field import field
from ._base import wraps
from . import widgets