from magicgui.widgets import __all__ as mgui_all
from magicgui.widgets import * # to avoid importing both magicgui.widgets and magicclass.widgets

from .listwidget import ListWidget
from .misc import Figure, ConsoleTextEdit, CheckButton
from .separator import Separator
from .sequence import ListEdit, TupleEdit
from .utils import FrozenContainer

try:
    from .console import QtConsole
except ImportError:
    pass

try:
    from .qtgraph import QtPlotCanvas, QtImageCanvas
except ImportError:
    pass

__all__ = ["ListWidget", 
           "Figure",
           "ConsoleTextEdit", 
           "CheckButton",
           "Separator",
           "ListEdit",
           "TupleEdit",
           "FrozenContainer",
           "QtConsole",
           "QtPlotCanvas",
           "QtImageCanvas",
           ]

__all__ += mgui_all