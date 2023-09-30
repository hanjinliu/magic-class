from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    overload,
    TypeVar,
    Callable,
)
from typing_extensions import Annotated
from magicgui.widgets import Widget, EmptyWidget

from magicclass.signature import split_annotated_type, is_annotated

try:
    from typing import _tp_cache
except ImportError:
    _tp_cache = lambda x: x

if TYPE_CHECKING:
    from magicclass.fields import MagicField

_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V", bound=object)

# fmt: off
@overload
def bound(obj: Callable[[_W], _V]) -> type[_V]: ...
@overload
def bound(obj: Callable[[Any, _W], _V]) -> type[_V]: ...
@overload
def bound(obj: MagicField[_W, _V]) -> type[_V]: ...
@overload
def bound(obj: type[_W]) -> type: ...
# fmt: on


def bound(obj):
    """Function version of ``Bound[...]``."""
    # NOTE: This could be more useful than Bound??
    from magicclass.fields import MagicField

    if callable(obj):
        outtype = obj.__annotations__.get("return", Any)
    elif isinstance(obj, MagicField):
        outtype = obj.annotation or Any
    elif isinstance(obj, (type, str)):
        outtype = Any
    else:
        raise TypeError("'bound' can only convert callable, MagicField or type objects")
    while is_annotated(outtype):
        outtype, _ = split_annotated_type(outtype)
    if isinstance(obj, str):
        obj = BoundLiteral(obj)
    return Annotated[outtype, {"bind": obj, "widget_type": EmptyWidget}]


class BoundLiteral:
    """
    A class used to represent a future evaluable expression.

    This object will be created when a string is passed to the ``Bound[...]`` type.
    """

    def __init__(self, expr: str):
        self._expr = expr

    def eval(self, cls: type) -> Any:
        from magicclass.utils import eval_attribute

        return eval_attribute(cls, self._expr)


class _BoundAlias(type):
    """
    This metaclass is necessary for ``mypy`` to reveal type.

    For instance, if type annotation is added like this

    >>> def _get_int(self, _=None) -> int:
    >>>     return 0

    >>> def func(self, x: Bound[_get_int]):
    >>>     # do something

    ``x`` will be considered to be ``Bound`` type otherwise.
    """

    @overload
    def __getitem__(cls, value: MagicField[_W, _V]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Callable[..., _V]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: type[_V]) -> type[_V]:
        ...

    @_tp_cache
    def __getitem__(cls, value):
        if isinstance(value, tuple):
            raise TypeError(
                "Bound[...] should be used with only one "
                "argument (the object to be bound)."
            )
        return bound(value)


class Bound(metaclass=_BoundAlias):
    """
    Make Annotated type from a MagicField or a method, such as:

    >>> from magicclass import magicclass, field
    >>> @magicclass
    >>> class MyClass:
    ...     i = field(int)
    ...     def func(self, v: Bound[i]):
    ...         ...

    ``Bound[value]`` is identical to ``Annotated[Any, {"bind": value}]``.
    """

    def __new__(cls, *args):
        raise TypeError(
            "`Bound(...)` is deprecated since 0.5.21. Bound is now a generic alias instead "
            "of a function. Please use `Bound[...]`."
        )

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Bound")
