from __future__ import annotations
import macrokit as mk
from macrokit import Expr, Head, symbol
from enum import Enum
from pathlib import Path
import datetime
from .types import Color
from .widgets import ColorEdit
from .widgets.sequence import ListDataView
from ._gui._base import MagicTemplate

# classes
_datetime = Expr(Head.getattr, [datetime, datetime.datetime])
_date = Expr(Head.getattr, [datetime, datetime.date])
_time = Expr(Head.getattr, [datetime, datetime.time])

# magicgui-style input
mk.register_type(Enum, lambda e: symbol(e.value))
mk.register_type(Path, lambda e: f"r'{e}'")
mk.register_type(ListDataView, lambda e: list(e))
mk.register_type(
    datetime.datetime,
    lambda e: Expr.parse_call(
        _datetime, (e.year, e.month, e.day, e.hour, e.minute), {}
    ),
)
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

if tuple(int(v) for v in mgui.__version__.split(".")[:2]) < (0, 4):
    # magicgui<0.4 has bug in type registration
    from magicgui.type_map import _TYPE_DEFS

    _TYPE_DEFS[Color] = (ColorEdit, {})
else:
    mgui.register_type(Color, widget_type=ColorEdit)
