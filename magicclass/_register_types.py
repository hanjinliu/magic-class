from __future__ import annotations
import macrokit as mk
from macrokit import Expr, Head, symbol
from enum import Enum
import pathlib
import datetime
from magicclass.types import Color, Path, ExprStr
from magicclass.widgets import ColorEdit, EvalLineEdit
from magicclass._gui._base import MagicTemplate

# classes
_datetime = Expr(Head.getattr, [datetime, datetime.datetime])
_date = Expr(Head.getattr, [datetime, datetime.date])
_time = Expr(Head.getattr, [datetime, datetime.time])
_timedelta = Expr(Head.getattr, [datetime, datetime.timedelta])

# magicgui-style input
mk.register_type(Enum, lambda e: symbol(e.value))
mk.register_type(pathlib.Path, lambda e: f"r'{e}'")
mk.register_type(float, lambda e: str(round(e, 8)))

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

mk.register_type(
    datetime.date, lambda e: Expr.parse_call(_date, (e.year, e.month, e.day), {})
)
mk.register_type(
    datetime.time, lambda e: Expr.parse_call(_time, (e.hour, e.minute), {})
)
mk.register_type(
    datetime.timedelta, lambda e: Expr.parse_call(_timedelta, (e.days, e.seconds), {})
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
mgui.register_type(Path.Save, widget_type="FileEdit", mode="w")
mgui.register_type(Path.Dir, widget_type="FileEdit", mode="d")
mgui.register_type(Path.Multiple, widget_type="FileEdit", mode="rm")
mgui.register_type(ExprStr, widget_type=EvalLineEdit)
