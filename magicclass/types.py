from __future__ import annotations
from enum import Enum
import typing
from typing import Any, Union, Iterable, overload, TYPE_CHECKING, TypeVar, Callable
from typing_extensions import Literal, Annotated, ParamSpec
from magicgui.widgets import Widget, EmptyWidget

from .fields import MagicField

try:
    from typing import _tp_cache
except ImportError:
    _tp_cache = lambda x: x

if TYPE_CHECKING:
    from typing_extensions import _AnnotatedAlias


class WidgetType(Enum):
    none = "none"
    scrollable = "scrollable"
    draggable = "draggable"
    split = "split"
    collapsible = "collapsible"
    hcollapsible = "hcollapsible"
    button = "button"
    toolbox = "toolbox"
    tabbed = "tabbed"
    stacked = "stacked"
    list = "list"
    subwindows = "subwindows"
    groupbox = "groupbox"
    frame = "frame"
    mainwindow = "mainwindow"


WidgetTypeStr = Union[
    Literal["none"],
    Literal["scrollable"],
    Literal["draggable"],
    Literal["split"],
    Literal["collapsible"],
    Literal["button"],
    Literal["toolbox"],
    Literal["tabbed"],
    Literal["stacked"],
    Literal["list"],
    Literal["subwindows"],
    Literal["groupbox"],
    Literal["frame"],
    Literal["mainwindow"],
    Literal["hcollapsible"],
]


PopUpModeStr = Union[
    Literal["popup"],
    Literal["first"],
    Literal["last"],
    Literal["above"],
    Literal["below"],
    Literal["dock"],
    Literal["parentlast"],
]


ErrorModeStr = Union[
    Literal["msgbox"],
    Literal["stderr"],
    Literal["stdout"],
]

Color = Union[Iterable[float], str]

_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V", bound=object)
_P = ParamSpec("_P")


@overload
def bound(obj: Callable[[_W], _V]) -> type[_V]:
    ...


@overload
def bound(obj: Callable[[Any, _W], _V]) -> type[_V]:
    ...


@overload
def bound(obj: MagicField[_W, _V]) -> type[_V]:
    ...


@overload
def bound(obj: type[_W]) -> type:
    ...


def bound(obj):
    """Function version of Bound[...]."""
    # NOTE: This could be more useful than Bound??
    if callable(obj):
        outtype = obj.__annotations__.get("return", Any)
    elif isinstance(obj, MagicField):
        outtype = obj.annotation or Any
    elif isinstance(obj, type):
        outtype = Any
    else:
        raise TypeError("'bound' can only convert callable, MagicField or type objects")
    return Annotated[outtype, {"bind": obj, "widget_type": EmptyWidget}]


class _BoundAlias(type):
    """
    This metaclass is necessary for ``mypy`` to reveal type.

    For instance, if type annotation is added like this

    .. code-block:: python

        def _get_int(self, _=None) -> int:
            return 0

        def func(self, x: Bound[_get_int]):
            # do something

    ``x`` will be considered to be ``Bound`` type otherwise.
    """

    @overload
    def __getitem__(cls, value: MagicField[_W, _V]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Callable[_P, _V]) -> type[_V]:
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

    .. code-block:: python

        from magicclass import magicclass, field

        @magicclass
        class MyClass:
            i = field(int)
            def func(self, v: Bound[i]):
                ...

    ``Bound[value]`` is identical to ``Annotated[Any, {"bind": value}]``.
    """

    def __new__(cls, *args):
        raise TypeError(
            "`Bound(...)` is deprecated since 0.5.21. Bound is now a generic alias instead "
            "of a function. Please use `Bound[...]`."
        )

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Bound")


_T = TypeVar("_T", bound=type)


class _OptionalAlias(type):
    @overload
    def __getitem__(cls, value: _T) -> type[typing.Optional[_T]]:
        ...

    @overload
    def __getitem__(cls, value: tuple[_T, dict[str, Any]]) -> type[typing.Optional[_T]]:
        ...

    def __getitem__(cls, value):
        if isinstance(value, tuple):
            type_, options = value
        else:
            type_, options = value, {}

        if not isinstance(type_, (type, typing._GenericAlias)):
            raise TypeError(
                "The first argument of Optional must be a type but "
                f"got {type(type_)}."
            )
        if not isinstance(options, dict):
            raise TypeError(
                "The second argument of Optional must be a dict but "
                f"got {type(options)}."
            )
        from .widgets import OptionalWidget

        opt = dict(
            widget_type=OptionalWidget,
            annotation=type_,
            options=options,
        )
        return Annotated[typing.Optional[type_], opt]


class Optional(metaclass=_OptionalAlias):
    """
    Make Annotated type similar to ``typing.Optional``.

    Arguments annotated with ``Optional[int]`` will create a
    ``OptionalWidget`` with a ``SpinBox`` as an inner widget.
    Arguments annotated with ``Optional[X, {...}]`` will create a
    ``OptionalWidget`` with a widget constructed using widget option
    ``{...}``.
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Optional cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Optional.")


_S = TypeVar("_S", bound=tuple)


class _TupleAlias(type):
    def __getitem__(cls, value: _S) -> type[_S]:
        from .widgets import TupleEdit

        type_ = typing.Tuple[value]
        opt = dict(
            widget_type=TupleEdit,
            annotation=type_,
        )
        return Annotated[type_, opt]


class Tuple(metaclass=_TupleAlias):
    """
    Make Annotated type similar to ``typing.Tuple``.

    Arguments annotated with ``Tuple[...]`` will create a
    ``TupleEdit`` with a annotated sub types.
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Tuple cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Tuple.")


class _ListAlias(type):
    def __getitem__(cls, value: _T) -> type[list[_T]]:
        from .widgets import ListEdit

        type_ = typing.List[value]
        opt = dict(
            widget_type=ListEdit,
            annotation=type_,
        )
        return Annotated[type_, opt]


class List(metaclass=_ListAlias):
    """
    Make Annotated type similar to ``typing.List``.

    Arguments annotated with ``List[...]`` will create a
    ``ListEdit`` with a annotated sub types.
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type List cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.List.")


"""
Examples
--------

from magicclass import magicclass, set_options
from magicclass.types import Tuple, List, Optional
@magicclass
class A:
    @set_options(a={"options": {"min": -1}})
    def f(self, a: Tuple[int, int]):
        print(a)
    @set_options(a={"options": {"min": -1}})
    def g(self, a: List[float]):
        print(a)
    @set_options(a={"options": {"min": -1}})
    def h(self, a: Optional[int]):
        print(a)
ui = A()
ui.show()

"""
