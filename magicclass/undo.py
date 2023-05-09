from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar, overload
from typing_extensions import ParamSpec
from abc import ABC, abstractmethod, abstractproperty

_P = ParamSpec("_P")
_R = TypeVar("_R")


class ImplementsUndo(ABC):
    @abstractmethod
    def run(self) -> None:
        """Run undo operation."""

    @abstractproperty
    def redo_action(self) -> RedoAction:
        """Enum of redo action."""


class UndoCallback(Generic[_R], ImplementsUndo):
    """Callback object that will be recognized by magic-classes."""

    def __init__(self, func: Callable[..., _R], *args, **kwargs) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._name = getattr(func, "__qualname__", repr(func))
        self._redo_action = RedoAction.Default

    def __repr__(self) -> str:
        return f"UndoCallback<{self._name}>"

    def run(self) -> _R:
        """Execute the undo operation."""
        return self._func(*self._args, **self._kwargs)

    @property
    def redo_action(self) -> RedoAction:
        return self._redo_action

    def copy(self) -> UndoCallback[_R]:
        """Return a copy of this undo operation."""
        out = self.__class__(self._func, *self._args, **self._kwargs)
        out._name = self._name
        out._redo_action = self._redo_action
        return out

    def with_args(self, *args, **kwargs) -> UndoCallback[_R]:
        """Return a new callback with updated arguments."""
        _kwargs = self._kwargs.copy()
        _kwargs.update(kwargs)
        new = self.__class__(self._func, *(self._args + args), **_kwargs)
        new._name = self._name
        return new

    def with_name(self, name: str) -> UndoCallback[_R]:
        """Return a new callback with the updated name."""
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        new = self.copy()
        new._name = name
        return new

    def with_redo(self, redo_func: Callable[[], Any]) -> UndoCallback[_R]:
        """Return a new callback with the updated redo function."""
        if not callable(redo_func):
            raise TypeError("redo_func must be callable")
        new = self.copy()
        new._redo_action = RedoAction.Custom(redo_func)
        return new

    def to_function(self) -> Callable[[], _R]:
        return lambda: self.run()


class _RedoAction:
    def matches(self, other) -> bool:
        return self is RedoAction(other)


class DefaultRedoAction(_RedoAction):
    redoable = True

    def __repr__(self) -> str:
        return "RedoAction.Default"


class NoRedoAction(_RedoAction):
    redoable = False

    def __repr__(self) -> str:
        return "RedoAction.Undefined"


class CustomRedoAction(_RedoAction):
    redoable = True

    def __init__(self, func: Callable[[], Any]):
        self._func = func

    def __repr__(self) -> str:
        return f"RedoAction.Custom({self._func!r})"

    def matches(self, other) -> bool:
        other = RedoAction(other)
        return other is RedoAction.Custom

    def run(self):
        return self._func()


class RedoAction:
    """A parametric Enum that defines the redo action of an undo operation."""

    Undefined = NoRedoAction()
    Default = DefaultRedoAction()
    Custom = CustomRedoAction

    def __new__(cls, value: _RedoAction | str) -> _RedoAction:
        if isinstance(value, str):
            return getattr(RedoAction, value.capitalize())
        elif isinstance(value, _RedoAction):
            return value
        else:
            raise TypeError(f"invalid redo action: {value}")


@overload
def undo_callback(
    func: Callable[..., _R], redo: Callable[[], Any] | bool = True
) -> UndoCallback[_R]:
    ...


@overload
def undo_callback(
    func: None = None, redo: Callable[[], Any] | bool = True
) -> Callable[[Callable[..., _R]], UndoCallback[_R]]:
    ...


def undo_callback(func=None, *, redo=True):
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

    def wrapper(f):
        if not callable(f):
            raise TypeError("`func` must be callable")
        cb = UndoCallback(f)
        if callable(redo):
            cb = cb.with_redo(redo)
        elif isinstance(redo, bool):
            if not redo:
                cb._redo_action = RedoAction.Undefined
        else:
            raise TypeError("redo must be callable or bool")
        return cb

    return wrapper if func is None else wrapper(func)
