from __future__ import annotations
import macrokit as mk
from macrokit import Expr, Head, symbol
from enum import Enum
from pathlib import Path
import datetime

from .types import Color
from .widgets import ColorEdit
from ._gui._base import MagicTemplate

# classes
_datetime = Expr(Head.getattr, [datetime, datetime.datetime])
_date = Expr(Head.getattr, [datetime, datetime.date])
_time = Expr(Head.getattr, [datetime, datetime.time])

# magicgui-style input
mk.register_type(Enum, lambda e: symbol(e.value))
mk.register_type(Path, lambda e: f"r'{e}'")

try:
    from magicgui.widgets._concrete import ListDataView
except ImportError:
    pass
else:
    mk.register_type(ListDataView, lambda e: list(e))

mk.register_type(
    datetime.datetime,
    lambda e: Expr.parse_call(
        _datetime, (e.year, e.month, e.day, e.hour, e.minute), {}
    ),
)


@mk.register_type(range)
def _fmt_range(e: range) -> str:
    if e.step == 1:
        if e.start == 0:
            return f"range({e.stop})"
        else:
            return f"range({e.start}, {e.stop})"
    else:
        return f"range({e.start}, {e.stop}, {e.step})"


mk.register_type(
    datetime.date, lambda e: Expr.parse_call(_date, (e.year, e.month, e.day), {})
)
mk.register_type(
    datetime.time, lambda e: Expr.parse_call(_time, (e.hour, e.minute), {})
)


@mk.register_type(MagicTemplate)
def find_myname(gui: MagicTemplate):
    """This function is the essential part of macro recording"""
    parent = gui.__magicclass_parent__
    if parent is None:
        return gui._my_symbol
    else:
        return Expr(Head.getattr, [find_myname(parent), gui._my_symbol])


import magicgui as mgui

mgui.register_type(Color, widget_type=ColorEdit)
