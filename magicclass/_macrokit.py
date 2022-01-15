from __future__ import annotations
from macrokit import Expr, register_type, Head
from enum import Enum
from pathlib import Path
import datetime
from .gui._base import MagicTemplate

# classes
_datetime = Expr(Head.getattr, [datetime, datetime.datetime])
_date = Expr(Head.getattr, [datetime, datetime.date])
_time = Expr(Head.getattr, [datetime, datetime.time])

# magicgui-style input
register_type(Enum, lambda e: repr(str(e.name)))
register_type(Path, lambda e: f"r'{e}'")
register_type(datetime.datetime, lambda e: Expr.parse_call(_datetime, (e.year, e.month, e.day, e.hour, e.minute), {}))
register_type(datetime.date, lambda e: Expr.parse_call(_date, (e.year, e.month, e.day), {}))
register_type(datetime.time, lambda e: Expr.parse_call(_time, (e.hour, e.minute), {}))

@register_type(MagicTemplate)
def find_myname(gui: MagicTemplate):
    """This function is the essential part of macro recording"""
    parent = gui.__magicclass_parent__
    if parent is None:
        return gui._my_symbol
    else:
        return Expr(Head.getattr, [find_myname(parent), gui._my_symbol])
