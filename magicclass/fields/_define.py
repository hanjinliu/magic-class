from __future__ import annotations
from typing import Any, TYPE_CHECKING, Callable

from ..utils import argcount

if TYPE_CHECKING:
    from .._gui._base import MagicTemplate


def define_callback(self: Any, callback: Callable):
    """Define a callback function from a method."""
    return callback.__get__(self)


def define_callback_gui(self: MagicTemplate, callback: Callable):
    """Define a callback function from a method of a magic-class."""

    *_, clsname, funcname = callback.__qualname__.split(".")
    mro = self.__class__.__mro__
    for base in mro:
        if base.__name__ == clsname:
            _func: Callable = getattr(base, funcname).__get__(self)
            _func = _normalize_argcount(_func)

            def _callback(v):
                with self.macro.blocked():
                    _func(v)
                return None

            break
    else:

        def _callback(v):
            # search for parent instances that have the same name.
            current_self = self
            while not (
                hasattr(current_self, funcname)
                and current_self.__class__.__qualname__.split(".")[-1] == clsname
            ):
                current_self = current_self.__magicclass_parent__
            _func = _normalize_argcount(getattr(current_self, funcname))

            with self.macro.blocked():
                _func(v)
            return None

    return _callback


def _normalize_argcount(func: Callable) -> Callable[[Any], Any]:
    if argcount(func) == 0:
        return lambda v: func()
    return func
