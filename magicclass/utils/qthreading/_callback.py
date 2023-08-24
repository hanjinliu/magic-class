from __future__ import annotations

from functools import partial, wraps
from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
    Iterable,
    Literal,
    TypeVar,
    Generic,
    overload,
)
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from magicclass._gui import BaseGui

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
        self, callback: Callable[[Any, _R1], _R2] | Callable[[Any], _R2] | None = None
    ) -> Callable[[Any, _R1], _R2] | Callable[[Any], _R2]:
        """
        Remove callback function from the callback list.

        Parameters
        ----------
        callback : Callable
            Callback function to be removed.
        """
        if callback is None:
            self._callbacks.clear()
            return None
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

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R1:
        return self._func(*args, **kwargs)

    def with_args(self, *args: _P.args, **kwargs: _P.kwargs) -> Callback[[], _R1]:
        """Return a partial callback."""
        return self.__class__(partial(self._func, *args, **kwargs))

    @overload
    def __get__(self, obj, type=None) -> Callback[..., _R1]:
        ...

    @overload
    def __get__(self, obj: Literal[None], type=None) -> Callback[_P, _R1]:
        ...

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return self.__class__(partial(self._func, obj))


class NestedCallback:
    def __init__(self, cb: Callable[..., Any], *args):
        self._cb = cb
        self._args = args

    def call(self):
        """Call the callback function."""
        return self._cb(*self._args)
