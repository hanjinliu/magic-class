from __future__ import annotations

from functools import partial, wraps
from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
    Iterable,
    TypeVar,
    Generic,
)
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from magicclass._gui import BaseGui
    from .thread_worker import thread_worker

_P = ParamSpec("_P")
_R1 = TypeVar("_R1")
_R2 = TypeVar("_R2")


class CallbackList(Generic[_R1]):
    """List of callback functions."""

    def __init__(self):
        self._callbacks: list[Callable[[Any, _R1], _R2] | Callable[[Any], _R2]] = []

    @property
    def callbacks(self) -> tuple[Callable[[Any, _R1], _R2] | Callable[[Any], _R2], ...]:
        return tuple(self._callbacks)

    def connect(
        self, callback: Callable[[Any, _R1], _R2] | Callable[[Any], _R2]
    ) -> Callable[[Any, _R1], _R2] | Callable[[Any], _R2]:
        """
        Append a callback function to the callback list.

        Parameters
        ----------
        callback : Callable
            Callback function.
        """
        if not callable(callback):
            raise TypeError("Can only connect callable object.")
        self._callbacks.append(callback)
        return callback

    def disconnect(
        self, callback: Callable[[Any, _R1], _R2] | Callable[[Any], _R2]
    ) -> Callable[[Any, _R1], _R2] | Callable[[Any], _R2]:
        """
        Remove callback function from the callback list.

        Parameters
        ----------
        callback : Callable
            Callback function to be removed.
        """
        self._callbacks.remove(callback)
        return callback

    def _iter_as_method(
        self, obj: BaseGui, filtered: bool = False
    ) -> Iterable[Callable]:
        for ref in self._callbacks:
            if not filtered:
                yield _make_method(ref, obj)
            else:
                yield _make_filtered_method(ref, obj)

    def _iter_as_nested_cb(
        self, gui: BaseGui, *args, filtered: bool = False
    ) -> Iterable[NestedCallback]:
        for c in self._iter_as_method(gui, filtered=filtered):
            yield NestedCallback(c, *args)


def _make_method(func, obj: BaseGui):
    def f(*args, **kwargs):
        with obj.macro.blocked():
            out = func.__get__(obj)(*args, **kwargs)
        return out

    return f


def _make_filtered_method(func, obj: BaseGui):
    def f(yielded):
        if isinstance(yielded, NestedCallback):
            return None
        with obj.macro.blocked():
            out = func.__get__(obj)(yielded)
        return out

    return f


class Callback(Generic[_P, _R1]):
    """Callback object that can be recognized by thread_worker."""

    def __init__(self, f: Callable[_P, _R1]):
        if not callable(f):
            raise TypeError(f"{f} is not callable.")
        self._func = f
        wraps(f)(self)

    @staticmethod
    def catch(out, gui: BaseGui, tw: thread_worker, args, kwargs, record=True):
        if isinstance(out, Callback):
            with gui.macro.blocked():
                out = out._func()
        if record and gui.macro.active and tw._recorder is not None:
            tw._recorder(gui, out, *args, **kwargs)

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R1:
        return self._func(*args, **kwargs)

    def with_args(self, *args, **kwargs):
        """Return a partial callback."""
        return self.__class__(partial(self._func, *args, **kwargs))

    def __get__(self, obj, type=None) -> Callback[_P, _R1]:
        if obj is None:
            return self
        return self.with_args(obj)


class NestedCallback:
    def __init__(self, cb: Callable[..., Any], gui: BaseGui, *args):
        self._cb = cb
        self._args = args
        self._gui = gui

    def call(self):
        with self._gui.macro.blocked():
            return self._cb(*self._args)
