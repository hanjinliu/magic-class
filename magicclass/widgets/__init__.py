"""
Advanced widgets for magic class GUI.
These widgets are all compatible with the ``append`` method of Container widgets.
"""

from magicgui.widgets import *  # to avoid importing both magicgui.widgets and magicclass.widgets

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
    ToolBoxContainer,
)
from .pywidgets import ListWidget, DictWidget
from .color import ColorEdit, ColorSlider
from .misc import (
    OptionalWidget,
    ConsoleTextEdit,
    CheckButton,
    RangeSlider,
    FloatRangeSlider,
    SpreadSheet,
)
from .plot import Figure, SeabornFigure
from .separator import Separator
from .sequence import ListEdit, TupleEdit
from .utils import FreeWidget
from .logger import Logger

__all__ = [
    "ButtonContainer",
    "ColorEdit",
    "ColorSlider",
    "ConsoleTextEdit",
    "CheckButton",
    "CollapsibleContainer",
    "DictWidget",
    "DraggableContainer",
    "FrameContainer",
    "Figure",
    "FloatRangeSlider",
    "FreeWidget",
    "GroupBoxContainer",
    "HCollapsibleContainer",
    "ListEdit",
    "ListContainer",
    "ListWidget",
    "Logger",
    "OptionalWidget",
    "RangeSlider",
    "SeabornFigure",
    "Separator",
    "ScrollableContainer",
    "SubWindowsContainer",
    "SplitterContainer",
    "SpreadSheet",
    "StackedContainer",
    "TabbedContainer",
    "ToolBoxContainer",
    "TupleEdit",
]
