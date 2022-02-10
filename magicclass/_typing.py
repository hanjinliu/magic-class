from __future__ import annotations

from enum import Enum
from typing import Union
from typing_extensions import Literal


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


WidgetTypeStr = Union[Literal["none"],
                      Literal["scrollable"],
                      Literal["draggable"],
                      Literal["split"],
                      Literal["collapsible"],
                      Literal["button"],
                      Literal["toolbox"],
                      Literal["tabbed"],
                      Literal["stacked"], 
                      Literal["list"],
                      Literal["subwindows"],
                      Literal["groupbox"],
                      Literal["frame"],
                      Literal["mainwindow"], 
                      Literal["hcollapsible"]
                      ]


PopUpModeStr = Union[Literal["popup"],
                     Literal["first"],
                     Literal["last"],
                     Literal["above"],
                     Literal["below"],
                     Literal["dock"],
                     Literal["parentlast"]
                     ]


ErrorModeStr = Union[Literal["msgbox"],
                     Literal["stderr"],
                     Literal["stdout"],
                     ]
