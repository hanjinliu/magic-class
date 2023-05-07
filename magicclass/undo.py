from __future__ import annotations

from typing import Callable, Generic, TypeVar

_R = TypeVar("_R")
_V = TypeVar("_V")


class ImplementsUndo:
    def call(self) -> None:
        raise NotImplementedError


class UndoFunction(Generic[_R], ImplementsUndo):
    def __init__(self, func: Callable[..., _R], *args, **kwargs) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def __repr__(self) -> str:
        return f"UndoFunction<{self._func!r}>"

    def call(self) -> _R:
        return self._func(*self._args, **self._kwargs)

    def with_args(self, *args, **kwargs) -> UndoFunction[_R]:
        _kwargs = self._kwargs.copy()
        _kwargs.update(kwargs)
        return UndoFunction(self._func, self._args + args, **_kwargs)


class SetterUndoFuncion(Generic[_V], ImplementsUndo):
    def __init__(self, setter: Callable[[_V], None], old_value: _V) -> None:
        self._setter = setter
        self._old_value = old_value

    def __repr__(self) -> str:
        return f"SetterUndoFuncion<{self._setter!r}>"

    def call(self) -> _R:
        return self._setter(self._old_value)


def to_undo(func: Callable[..., _R]) -> UndoFunction[_R]:
    if not callable(func):
        raise TypeError("func must be callable")
    return UndoFunction(func)
