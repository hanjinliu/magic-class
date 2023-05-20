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
from .colormap import ColormapEdit
from .misc import (
    OptionalWidget,
    ConsoleTextEdit,
    CheckButton,
    HistoryLineEdit,
    HistoryFileEdit,
    SpreadSheet,
)
from .plot import Figure, SeabornFigure
from .separator import Separator
from .utils import FreeWidget
from .logger import Logger
from .codeedit import CodeEdit
from .toggle_switch import ToggleSwitch
from .eval import EvalLineEdit

__all__ = [
    "ButtonContainer",
    "CodeEdit",
    "ColorEdit",
    "ColormapEdit",
    "ColorSlider",
    "ConsoleTextEdit",
    "CheckButton",
    "CollapsibleContainer",
    "DictWidget",
    "DraggableContainer",
    "EvalLineEdit",
    "FrameContainer",
    "Figure",
    "FreeWidget",
    "GroupBoxContainer",
    "HCollapsibleContainer",
    "HistoryFileEdit",
    "HistoryLineEdit",
    "ListContainer",
    "ListWidget",
    "Logger",
    "OptionalWidget",
    "SeabornFigure",
    "Separator",
    "ScrollableContainer",
    "SubWindowsContainer",
    "SplitterContainer",
    "SpreadSheet",
    "StackedContainer",
    "TabbedContainer",
    "ToggleSwitch",
    "ToolBoxContainer",
]
