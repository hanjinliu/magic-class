from __future__ import annotations

from typing import Callable, Generic, TypeVar
from typing_extensions import ParamSpec
from abc import ABC, abstractmethod

_P = ParamSpec("_P")
_R = TypeVar("_R")


class ImplementsUndo(ABC):
    @abstractmethod
    def call(self) -> None:
        raise NotImplementedError


class UndoCallback(Generic[_R], ImplementsUndo):
    """Callback object that will be recognized by magic-classes."""

    def __init__(self, func: Callable[..., _R], *args, **kwargs) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._name = getattr(func, "__qualname__", repr(func))

    def __repr__(self) -> str:
        return f"UndoCallback<{self._name}>"

    def call(self) -> _R:
        """Execute the undo operation."""
        return self._func(*self._args, **self._kwargs)

    def copy(self) -> UndoCallback[_R]:
        """Return a copy of this undo operation."""
        return self.__class__(self._func, *self._args, **self._kwargs)

    def with_args(self, *args, **kwargs) -> UndoCallback[_R]:
        _kwargs = self._kwargs.copy()
        _kwargs.update(kwargs)
        new = self.__class__(self._func, *(self._args + args), **_kwargs)
        new._name = self._name
        return new

    def with_name(self, name: str) -> UndoCallback[_R]:
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        new = self.copy()
        new._name = name
        return new

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
