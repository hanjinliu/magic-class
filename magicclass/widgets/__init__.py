"""
Advanced widgets for magic class GUI.
These widgets are all compatible with the ``append`` method of Container widgets.
"""

from magicgui.widgets import * # to avoid importing both magicgui.widgets and magicclass.widgets

from .containers import (
    ButtonContainer,
    GroupBoxContainer,
    FrameContainer,
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
from .utils import FreeWidget


__all__ = ["ListWidget", 
           "Figure",
           "ConsoleTextEdit",
           "CheckButton",
           "Separator",
           "ListEdit",
           "DictWidget",
           "TupleEdit",
           "FreeWidget",
           "ButtonContainer",
           "GroupBoxContainer",
           "FrameContainer",
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
