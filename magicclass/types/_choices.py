from __future__ import annotations

from typing import (
    Any,
    Iterable,
    overload,
    TypeVar,
    Callable,
)
from typing_extensions import Annotated

try:
    from typing import _tp_cache
except ImportError:
    _tp_cache = lambda x: x


_V = TypeVar("_V", bound=object)


class _OneOfAlias(type):
    """metaclass of `OneOf`."""

    @overload
    def __getitem__(cls, value: Callable[..., Iterable[tuple[Any, _V]]]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Callable[..., Iterable[_V]]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[tuple[Any, _V]]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[_V]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: slice) -> type[int | float]:
        ...

    @_tp_cache
    def __getitem__(cls, value):
        if callable(value):
            outtype = value.__annotations__.get("return", Any)
        elif hasattr(value, "__iter__"):
            outtype = Any
        elif isinstance(value, slice):
            outtype, value = _normalize_slice(value)
        else:
            raise TypeError("'bound' can only convert callable or iterable objects.")
        return Annotated[outtype, {"choices": value, "nullable": False}]


def _normalize_slice(value: slice) -> type | list:
    start, stop, step = value.start or 0, value.stop or 0, value.step or 1
    if float in [type(start), type(stop), type(step)]:
        import math

        ndigits = -int(min(math.log10(start), math.log10(stop), math.log10(step))) + 4
        outtype = float
        outvalue: list[float] = []
        if step > 0:
            x = start
            while x < stop:
                outvalue.append(x)
                x = round(x + step, ndigits)
        else:
            x = stop
            while start < x:
                outvalue.append(x)
                x = round(x + step, ndigits)

    else:
        outtype = int
        outvalue = list(range(start, stop, step))
    return outtype, outvalue


class OneOf(metaclass=_OneOfAlias):
    """
    Make Annotated type from a method, such as:

    >>> from magicclass import magicclass
    >>> @magicclass
    >>> class MyClass:
    >>>     def func(self, v: OneOf[(1, 2, 3)]):
    >>>         ...

    `OneOf[value]` is identical to `Annotated[Any, {"choices": value}]`.
    """

    def __new__(cls, *args):
        raise TypeError("OneOf cannot be instantiated. Use OneOf[...] instead.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.{cls.__name__}")


Choices = OneOf  # alias


class _SomeOfAlias(type):
    """This metaclass is necessary for `mypy` to reveal type."""

    @overload
    def __getitem__(
        cls, value: Callable[..., Iterable[tuple[Any, _V]]]
    ) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: Callable[..., Iterable[_V]]) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[tuple[Any, _V]]) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[_V]) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: slice) -> type[int | float]:
        ...

    @_tp_cache
    def __getitem__(cls, value):
        if callable(value):
            outtype = value.__annotations__.get("return", Any)
        elif hasattr(value, "__iter__"):
            outtype = Any
        elif isinstance(value, slice):
            outtype, value = _normalize_slice(value)
        else:
            raise TypeError("'bound' can only convert callable or iterable objects.")
        return Annotated[
            outtype, {"choices": value, "nullable": False, "widget_type": "Select"}
        ]


class SomeOf(metaclass=_SomeOfAlias):
    """
    Make Annotated type from a method, such as:

    >>> from magicclass import magicclass

    >>> @magicclass
    >>> class MyClass:
    >>>     def func(self, v: Choices[(1, 2, 3)]):
    >>>         ...

    `Choices[value]` is identical to `Annotated[Any, {"choices": value}]`.
    """

    def __new__(cls, *args):
        raise TypeError("SomeOf cannot be instantiated. Use SomeOf[...] instead.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.SomeOf")
