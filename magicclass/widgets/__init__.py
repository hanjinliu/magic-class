"""
Advanced widgets for magic class GUI.
These widgets are all compatible with the ``append`` method of Container widgets.
"""

from magicgui.widgets import * # to avoid importing both magicgui.widgets and magicclass.widgets

from .containers import (
    ButtonContainer,
    GroupBoxContainer,
    ListContainer,
    SubWindowsContainer,
    ScrollableContainer,
    DraggableContainer,
    CollapsibleContainer,
    HCollapsibleContainer,
    SplitterContainer,
    StackedContainer,
    TabbedContainer,
    ToolBoxContainer
    )
from .pywidgets import ListWidget, DictWidget
from .misc import Figure, ConsoleTextEdit, CheckButton
from .separator import Separator
from .sequence import ListEdit, TupleEdit
from .threading import ProgressWidget, progress
from .utils import FreeWidget

try:
    from .console import QtConsole
except ImportError:
    from .utils import NotInstalled
    msg = "Module 'qtconsole' is not installed. To use QtConsole, " \
          "you have to install it by:\n" \
          "   $ pip install qtconsole\n" \
          "or\n" \
          "   $ conda install qtconsole"
          
    QtConsole = NotInstalled(msg)

from .qtgraph import *
from .napari import *
from .pyvista import *


__all__ = ["ListWidget", 
           "Figure",
           "ConsoleTextEdit", 
           "MacroEdit",
           "CheckButton",
           "Separator",
           "ListEdit",
           "DictWidget",
           "TupleEdit",
           "ProgressWidget",
           "progress",
           "FreeWidget",
           "ButtonContainer",
           "GroupBoxContainer",
           "ListContainer",
           "SubWindowsContainer",
           "ScrollableContainer",
           "DraggableContainer",
           "CollapsibleContainer",
           "HCollapsibleContainer",
           "SplitterContainer",
           "StackedContainer",
           "TabbedContainer",
           "ToolBoxContainer",
           "QtConsole",
           "QtPlotCanvas",
           "QtMultiPlotCanvas", 
           "Qt2YPlotCanvas",
           "QtImageCanvas",
           "QtMultiImageCanvas",
           "NapariCanvas",
           ]
