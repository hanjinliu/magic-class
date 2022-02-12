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
from .color import ColorEdit, ColorSlider
from .misc import Figure, OptionalWidget, ConsoleTextEdit, CheckButton, SpreadSheet
from .separator import Separator
from .sequence import ListEdit, TupleEdit
from .utils import FreeWidget


__all__ = ["ListWidget", 
           "Figure",
           "OptionalWidget",
           "ColorEdit",
           "ColorSlider",
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
           "SpreadSheet",
           "StackedContainer",
           "TabbedContainer",
           "ToolBoxContainer",
           ]
