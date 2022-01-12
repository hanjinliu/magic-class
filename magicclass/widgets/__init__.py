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

from .qtconsole import *
from .qtgraph import *
from .napari import *
from .pyvista import *


__all__ = ["ListWidget", 
           "Figure",
           "ConsoleTextEdit",
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
           ]
