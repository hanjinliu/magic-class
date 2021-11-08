"""
Advanced widgets for magic class GUI.
These widgets are all compatible with the ``append`` method of Container widgets.
"""

from magicgui.widgets import __all__ as mgui_all
from magicgui.widgets import * # to avoid importing both magicgui.widgets and magicclass.widgets

from .listwidget import ListWidget
from .misc import Figure, ConsoleTextEdit, CheckButton
from .separator import Separator
from .sequence import ListEdit, TupleEdit
from .utils import FrozenContainer

class NotInstalled:
    def __init__(self, msg):
        self.msg = msg
    
    def __getattr__(self, key: str):
        raise ModuleNotFoundError(self.msg)
    
    def __call__(self, *args, **kwargs):
        raise ModuleNotFoundError(self.msg)

try:
    from .console import QtConsole
except ImportError:
    msg = "Module 'qtconsole' is not installed. To use QtConsole, " \
          "you have to install it by:\n" \
          "   $ pip install qtconsole\n" \
          "or\n" \
          "   $ conda install qtconsole"
          
    QtConsole = NotInstalled(msg)

try:
    from .qtgraph import QtPlotCanvas, QtImageCanvas
except ImportError:
    msg = "Module 'pyqtgraph' is not installed. To use {}, " \
          "you have to install it by:\n" \
          "   $ pip install pyqtgraph\n" \
          "or\n" \
          "   $ conda install pyqtgraph -c conda forge"
    QtPlotCanvas = NotInstalled(msg.format("QtPlotCanvas"))
    QtImageCanvas = NotInstalled(msg.format("QtImageCanvas"))
    

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