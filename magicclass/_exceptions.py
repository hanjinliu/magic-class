from __future__ import annotations

from typing import Callable
from psygnal import EmitLoopError


class Canceled(RuntimeError):
    """Raised when a function is canceled"""


class Aborted(RuntimeError):
    """Raised when worker is aborted."""

    @classmethod
    def raise_(cls, *args):
        """A function version of "raise"."""
        if not args:
            args = ("Aborted.",)
        raise cls(*args)


class PreviewError(Exception):
    """Error raised during preview."""

    def __init__(self, exc: Exception, target_func: Callable):
        _target_qualname = getattr(target_func, "__qualname__", repr(target_func))
        self.__cause__ = exc
        super().__init__(
            f"{type(self).__name__}: Error calling preview function of "
            f"`{_target_qualname}`...\n{type(exc).__name__}: {exc}"
        )


class MagicClassConstructionError(Exception):
    """Raised when class definition is not a valid magic-class."""


class MagicGuiBuildError(RuntimeError):
    """Error raised when magicgui cannot build a gui."""


class AbstractAPIError(Exception):
    """Raised when an abstract API is called."""


def unwrap_errors(e: Exception) -> Exception:
    while isinstance(e, (EmitLoopError, PreviewError)):
        e = e.__cause__
    return e
