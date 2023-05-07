from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar, Generator
from typing_extensions import ParamSpec
from abc import ABC, abstractmethod
from functools import wraps
import inspect

_P = ParamSpec("_P")
_R = TypeVar("_R")


class ImplementsUndo(ABC):
    @abstractmethod
    def call(self) -> None:
        raise NotImplementedError


class UndoCallback(Generic[_R], ImplementsUndo):
    def __init__(self, func: Callable[..., _R], *args, **kwargs) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def __repr__(self) -> str:
        return f"UndoFunction<{self._func!r}>"

    def call(self) -> _R:
        return self._func(*self._args, **self._kwargs)

    def with_args(self, *args, **kwargs) -> UndoCallback[_R]:
        _kwargs = self._kwargs.copy()
        _kwargs.update(kwargs)
        return self.__class__(self._func, self._args + args, **_kwargs)

    def to_function(self) -> Callable[[], _R]:
        return lambda: self.call()


def undo_callback(func: Callable[..., _R]) -> UndoCallback[_R]:
    """
    Returns a undo operation that can be recognized by magic-classes.

    Examples
    --------
    >>> @magicclass
    >>> class A:
    ...     def func(self, x: int):
    ...         old_value = self._value  # save old value
    ...         self._value = x          # do
    ...         @undo_callback
    ...         def undo():
    ...             self._value = old_value  # undo
    ...         return undo
    """
    if not callable(func):
        raise TypeError("func must be callable")
    return UndoCallback(func)


def undoable(func: Callable[_P, Generator[_R, Any, Any]]) -> Callable[_P, _R]:
    """
    Convert a generator function into an undoable function.

    This is a convenience decorator for implementing undo operations without
    using the ``undo_callback`` directly. You can use ``yield`` to separate
    the "do" and "undo" parts of the function.

    Examples
    --------
    >>> @magicclass
    >>> class A:
    ...     @undoable
    ...     def func(self, x: int):
    ...         old_value = self._value  # save old value
    ...         self._value = x          # do
    ...         yield
    ...         self._value = old_value  # undo
    """
    if not inspect.isgeneratorfunction(func):
        raise TypeError("cannot decorate generator functions")

    @wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        next(gen)

        @undo_callback
        def out():
            try:
                next(gen)
            except StopIteration as e:
                return e.value
            else:
                raise RuntimeError("generator did not stop")

        return out

    return wrapper
