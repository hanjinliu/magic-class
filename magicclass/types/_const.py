from __future__ import annotations

from enum import Enum
from typing import Literal, Union, Iterable, Dict
import datetime
import pathlib


class WidgetType(Enum):
    none = "none"
    scrollable = "scrollable"
    draggable = "draggable"
    split = "split"
    collapsible = "collapsible"
    hcollapsible = "hcollapsible"
    button = "button"
    toolbox = "toolbox"
    tabbed = "tabbed"
    stacked = "stacked"
    list = "list"
    subwindows = "subwindows"
    groupbox = "groupbox"
    frame = "frame"
    mainwindow = "mainwindow"


WidgetTypeStr = Literal[
    "none",
    "scrollable",
    "draggable",
    "split",
    "collapsible",
    "button",
    "toolbox",
    "tabbed",
    "stacked",
    "list",
    "subwindows",
    "groupbox",
    "frame",
    "mainwindow",
    "hcollapsible",
]


PopUpModeStr = Literal[
    "popup",
    "first",
    "last",
    "above",
    "below",
    "dock",
    "dialog",
    "parentlast",
]


ErrorModeStr = Literal["msgbox", "stderr", "stdout"]

Color = Union[Iterable[float], str]
Colormap = Dict[float, Color]

MGUI_SIMPLE_TYPES = (
    Union[
        int,
        float,
        bool,
        str,
        pathlib.Path,
        datetime.datetime,
        datetime.date,
        datetime.time,
        Enum,
        range,
        slice,
        list,
        tuple,
    ],
)
