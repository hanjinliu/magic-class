"""magicgui-compatible widgets."""

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
    HistoryLineEdit,
    HistoryFileEdit,
    SpreadSheet,
)
from .plot import Figure, SeabornFigure
from .separator import Separator
from .utils import FreeWidget
from .logger import Logger
from .runner import CommandRunner
from .codeedit import CodeEdit

__all__ = [
    "ButtonContainer",
    "CodeEdit",
    "ColorEdit",
    "ColorSlider",
    "ConsoleTextEdit",
    "CheckButton",
    "CollapsibleContainer",
    "CommandRunner",
    "DictWidget",
    "DraggableContainer",
    "FrameContainer",
    "Figure",
    "FloatRangeSlider",
    "FreeWidget",
    "GroupBoxContainer",
    "HCollapsibleContainer",
    "HistoryFileEdit",
    "HistoryLineEdit",
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
]
