from __future__ import annotations

import time
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
            ncb = NestedCallback(c).with_args(*args)
            yield ncb
            ncb.await_call()


def _make_method(func, obj: BaseGui):
    def f(*args):
        if args and isinstance(args[0], Callback):
            return None
        with obj.macro.blocked():
            out = func.__get__(obj)(*args)
        return out

    return f


def _make_filtered_method(func, obj: BaseGui):
    def f(yielded):
        if isinstance(yielded, (Callback, NestedCallback)):
            return None
        with obj.macro.blocked():
            out = func.__get__(obj)(yielded)
        return out

    return f


class _AwaitableCallback(Generic[_P, _R1]):
    def __init__(self, f: Callable[_P, _R1]):
        if not callable(f):
            raise TypeError(f"{f} is not callable.")
        self._func = f
        wraps(f)(self)
        self._called = False

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R1:
        self._called = False
        out = self._func(*args, **kwargs)
        self._called = True
        return out

    def with_args(
        self, *args: _P.args, **kwargs: _P.kwargs
    ) -> _AwaitableCallback[[], _R1]:
        """Return a partial callback."""
        return self.__class__(partial(self._func, *args, **kwargs))

    def copy(self) -> _AwaitableCallback[_P, _R1]:
        """Return a copy of the callback."""
        return self.__class__(self._func)

    def await_call(self, timeout: float = -1) -> None:
        """
        Await the callback to be called.

        Usage
        -----
        >>> cb = thread_worker.callback(func)
        >>> yield cb
        >>> cb.await_call()  # stop here until callback is called
        """
        if timeout <= 0:
            while not self._called:
                time.sleep(0.01)
            return None
        t0 = time.time()
        while not self._called:
            time.sleep(0.01)
            if time.time() - t0 > timeout:
                raise TimeoutError(
                    f"Callback {self} did not finish within {timeout} seconds."
                )
        return None


class Callback(_AwaitableCallback[_P, _R1]):
    """Callback object that can be recognized by thread_worker."""

    @overload
    def __get__(self, obj: Any, type=None) -> Callback[..., _R1]:
        ...

    @overload
    def __get__(self, obj: Literal[None], type=None) -> Callback[_P, _R1]:
        ...

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return self.__class__(partial(self._func, obj))

    def with_args(self, *args: _P.args, **kwargs: _P.kwargs) -> Callback[[], _R1]:
        """Return a partial callback."""
        return self.__class__(partial(self._func, *args, **kwargs))


class NestedCallback(_AwaitableCallback[_P, _R1]):
    def with_args(self, *args: _P.args, **kwargs: _P.kwargs) -> NestedCallback[_P, _R1]:
        """Return a partial callback."""
        return self.__class__(partial(self._func, *args, **kwargs))
