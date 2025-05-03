from __future__ import annotations
from enum import Enum, auto

import time
from functools import wraps
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
    from magicclass.utils.qthreading._progressbar import _SupportProgress

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


class _partial:
    def __init__(self, fn, *args, **kwargs):
        if not isinstance(fn, _partial):
            self._fn = fn
            self._args = args
            self._kwargs = kwargs
        else:
            self._fn = fn._fn
            self._args = fn._args + args
            self._kwargs = {**fn._kwargs, **kwargs}
        self.__name__ = self._fn.__name__

    def __call__(self, *args, **kwargs):
        return self._fn(*self._args, *args, **self._kwargs, **kwargs)


class CallState(Enum):
    NOT_CALLED = auto()
    CALLED = auto()
    ERRORED = auto()


class _AwaitableCallback(Generic[_P, _R1]):
    def __init__(self, f: Callable[_P, _R1], desc: str | None = None):
        if not callable(f):
            raise TypeError(f"{f} is not callable.")
        self._func = f
        wraps(f)(self)
        self._called = CallState.NOT_CALLED
        self._progress_desc = desc

    def __repr__(self) -> str:
        fname = getattr(self._func, "__name__", repr(self._func))
        return f"{self.__class__.__name__}<{fname}>"

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R1:
        self._called = CallState.NOT_CALLED
        try:
            out = self._func(*args, **kwargs)
        except Exception as e:
            self._called = CallState.ERRORED
            if type(e) is RuntimeError and str(e).startswith(
                "wrapped C/C++ object of type"
            ):
                # to avoid the exception raised after GUI quit
                return None
            raise e
        else:
            self._called = CallState.CALLED
        return out

    def with_args(
        self, *args: _P.args, **kwargs: _P.kwargs
    ) -> _AwaitableCallback[[], _R1]:
        """Return a partial callback."""
        return self.__class__(_partial(self._func, *args, **kwargs))

    def with_desc(self, desc: str) -> _AwaitableCallback[_P, _R1]:
        """Set progress description."""
        return self.__class__(self._func, desc=desc)

    def copy(self) -> _AwaitableCallback[_P, _R1]:
        """Return a copy of the callback."""
        return self.__class__(self._func)

    def await_call(self, timeout: float = 60.0) -> None:
        """Await the callback to be called.

        Usage
        -----
        >>> cb = thread_worker.callback(func)
        >>> yield cb
        >>> cb.await_call()  # stop here until callback is called
        """
        if timeout <= 0:
            while self._called is CallState.NOT_CALLED:
                time.sleep(0.01)
        else:
            t0 = time.time()
            while self._called is CallState.NOT_CALLED:
                time.sleep(0.01)
                if time.time() - t0 > timeout:
                    s = "s" if timeout > 1 else ""
                    raise TimeoutError(
                        f"Callback {self} did not finish within {timeout} second{s}."
                    )
        if self._called is CallState.ERRORED:
            raise RuntimeError(f"Callback {self} raised an error.")
        return None

    @property
    def progress_desc(self) -> str | None:
        """Get the progress description."""
        return self._progress_desc

    def update_pbar_and_unwrap(self, pbar: _SupportProgress | None) -> _R1:
        if self.progress_desc is not None and pbar is not None:
            pbar.set_description(self.progress_desc)
        return self()


class Callback(_AwaitableCallback[_P, _R1]):
    """Callback object that can be recognized by thread_worker."""

    @overload
    def __get__(self, obj: Any, type=None) -> Callback[..., _R1]: ...

    @overload
    def __get__(self, obj: Literal[None], type=None) -> Callback[_P, _R1]: ...

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return self.__class__(_partial(self._func, obj))

    def with_args(self, *args: _P.args, **kwargs: _P.kwargs) -> Callback[[], _R1]:
        """Return a partial callback."""
        return self.__class__(_partial(self._func, *args, **kwargs))

    def arun(self, *args: _P.args, **kwargs: _P.kwargs) -> CallbackTask[_R1]:
        """Run the callback in a thread."""
        return CallbackTask(self.with_args(*args, **kwargs))


class NestedCallback(_AwaitableCallback[_P, _R1]):
    def with_args(self, *args: _P.args, **kwargs: _P.kwargs) -> NestedCallback[_P, _R1]:
        """Return a partial callback."""
        return self.__class__(_partial(self._func, *args, **kwargs))


class CallbackTask(Generic[_R1]):
    """A class to make the syntax of thread_worker and Callback similar."""

    def __init__(self, callback: Callback[[], _R1]):
        self._callback = callback

    def __iter__(self):
        yield self._callback
        self._callback.await_call()
