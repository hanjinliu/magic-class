from __future__ import annotations
from abc import ABCMeta
from collections import defaultdict

import pathlib
import datetime
from enum import Enum
import typing
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Hashable,
    Union,
    Iterable,
    overload,
    TypeVar,
    Callable,
    Literal,
    List,
    Sequence,
)
from typing_extensions import Annotated, _AnnotatedAlias
from magicgui.widgets import Widget, EmptyWidget

from magicclass.signature import split_annotated_type
from magicclass.utils import is_type_like

try:
    from typing import _tp_cache
except ImportError:
    _tp_cache = lambda x: x

if TYPE_CHECKING:
    from magicgui.widgets import FunctionGui
    from magicgui.widgets.bases import CategoricalWidget
    from typing_extensions import Self
    from magicclass.fields import MagicField

__all__ = [
    "WidgetType",
    "bound",
    "Bound",
    "Choices",
    "OneOf",
    "SomeOf",
    "Optional",
    "Union",
]

_T = TypeVar("_T")
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")
_U = TypeVar("_U")


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


WidgetTypeStr = Literal[
    "none",
    "scrollable",
    "draggable",
    "split",
    "collapsible",
    "button",
    "toolbox",
    "tabbed",
    "stacked",
    "list",
    "subwindows",
    "groupbox",
    "frame",
    "mainwindow",
    "hcollapsible",
]


PopUpModeStr = Literal[
    "popup",
    "first",
    "last",
    "above",
    "below",
    "dock",
    "dialog",
    "parentlast",
]


ErrorModeStr = Literal["msgbox", "stderr", "stdout"]

Color = Union[Iterable[float], str]

MGUI_SIMPLE_TYPES = (
    Union[
        int,
        float,
        bool,
        str,
        pathlib.Path,
        datetime.datetime,
        datetime.date,
        datetime.time,
        Enum,
        range,
        slice,
        list,
        tuple,
    ],
)


# Expression string
class _ExprInMeta(type):
    def __getitem__(cls, ns: dict[str, Any]) -> type[ExprStr]:
        if not isinstance(ns, dict):
            raise TypeError("namespace must be a dict")
        return Annotated[ExprStr, {"namespace": ns}]


class _ExprIn(metaclass=_ExprInMeta):
    def __new__(cls, *args, **kwargs):
        raise TypeError("ExprStr.In cannot be instantiated")


class ExprStr(str):
    """
    An expression string.

    `ExprStr` is a subclass of str that will be considered as an evaluation expression.
    `magicgui` interpret this type as a `EvalLineEdit`.

    >>> @magicgui
    >>> def func(x: ExprStr): ...

    >>> import numpy as np
    >>> @magicgui
    >>> def func(x: ExprStr.In[{"np": np}]): ...  # with given dict as namespace
    """

    In = _ExprIn

    def __new__(cls, x, ns: dict[str, Any] | None = None):
        self = str.__new__(cls, x)
        self.__ns = ns or {}
        return self

    def eval(self):
        """Evaluate the expression string."""
        return eval(str(self), self.__ns, {})


# Bound type

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
    while isinstance(outtype, _AnnotatedAlias):
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
        from .utils import eval_attribute

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


# Path type


class _AnnotatedPathAlias(type):
    _file_edit_mode: str

    def __getitem__(cls, filter: str) -> Self:
        return Annotated[pathlib.Path, {"mode": cls._file_edit_mode, "filter": filter}]


class _AnnotatedPathAlias2(_AnnotatedPathAlias):
    def __instancecheck__(cls, instance: Any) -> bool:
        return isinstance(instance, pathlib.Path)

    def __subclasscheck__(cls, subclass: type) -> bool:
        return issubclass(subclass, pathlib.Path)


class _AnnotatedMultiPathAlias(ABCMeta):
    def __getitem__(cls, filter: str) -> Self:
        return Annotated[List[Path], {"mode": "rm", "filter": filter}]


class _Path(pathlib.Path, metaclass=_AnnotatedPathAlias):
    _file_edit_mode = "r"


class _SavePath(_Path):
    _file_edit_mode = "w"


class _DirPath(_Path):
    _file_edit_mode = "d"


class _MultiplePaths(Sequence[pathlib.Path], metaclass=_AnnotatedMultiPathAlias):
    pass


class Path(pathlib.Path, metaclass=_AnnotatedPathAlias2):
    """
    A subclass of ``pathlib.Path`` with additional type annotation variations.

    >>> Path  # identical to pathlib.Path for magicgui
    >>> Path.Read  # pathlib.Path with mode "r" (identical to Path)
    >>> Path.Save  # pathlib.Path with mode "w"
    >>> Path.Dir  # pathlib.Path with mode "d"
    >>> Path.Multiple  # pathlib.Path with mode "rm"
    >>> Path.Read["*.py"]  # pathlib.Path with mode "r" and filter "*.py"
    """

    _file_edit_mode = "r"

    Read = _Path
    Save = _SavePath
    Dir = _DirPath
    Multiple = _MultiplePaths

    def __new__(cls, *args, **kwargs):
        return pathlib.Path(*args, **kwargs)


# OneOf/SomeOf types


class _OneOfAlias(type):
    """metaclass of ``OneOf``."""

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

    ``OneOf[value]`` is identical to ``Annotated[Any, {"choices": value}]``.
    """

    def __new__(cls, *args):
        raise TypeError("OneOf cannot be instantiated. Use OneOf[...] instead.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.{cls.__name__}")


Choices = OneOf  # alias


class _SomeOfAlias(type):
    """This metaclass is necessary for ``mypy`` to reveal type."""

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

    ``Choices[value]`` is identical to ``Annotated[Any, {"choices": value}]``.
    """

    def __new__(cls, *args):
        raise TypeError("SomeOf cannot be instantiated. Use SomeOf[...] instead.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.SomeOf")


# Optional type


class _OptionalAlias(type):
    @overload
    def __getitem__(cls, value: type[_T]) -> type[typing.Optional[_T]]:
        ...

    @overload
    def __getitem__(
        cls, value: tuple[type[_T], dict[str, Any]]
    ) -> type[typing.Optional[_T]]:
        ...

    def __getitem__(cls, value):
        if not is_type_like(value):
            raise TypeError(
                "The first argument of Optional must be a type but "
                f"got {type(value)}."
            )
        from .widgets import OptionalWidget

        opt = dict(widget_type=OptionalWidget)
        if isinstance(value, _AnnotatedAlias):
            type0, opt0 = split_annotated_type(value)
            type_ = typing.Optional[type0]
            opt.update(annotation=type_, options=opt0)
            return Annotated[type_, opt]
        else:
            opt.update(annotation=typing.Optional[value])
            return Annotated[typing.Optional[value], opt]


class Optional(metaclass=_OptionalAlias):
    """
    Make Annotated type similar to ``typing.Optional``.

    Arguments annotated with ``Optional[int]`` will create a
    ``OptionalWidget`` with a ``SpinBox`` as an inner widget.

    >>> from magicclass import magicclass, set_options
    >>> from magicclass.types import Optional

    >>> @magicclass
    >>> class A:
    >>>     @set_options(a={"options": {"min": -1}})
    >>>     def f(self, a: Optional[int]):
    >>>         print(a)

    >>> ui = A()
    >>> ui.show()
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Optional cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Optional.")


# Union type


class _UnionAlias(type):
    @overload
    def __getitem__(cls, value: tuple[_T, _T1]) -> typing.Union[_T, _T1]:
        ...

    @overload
    def __getitem__(cls, value: tuple[_T, _T1, _T2]) -> typing.Union[_T, _T1, _T2]:
        ...

    @overload
    def __getitem__(
        cls, value: tuple[_T, _T1, _T2, _T3]
    ) -> typing.Union[_T, _T1, _T2, _T3]:
        ...

    def __getitem__(cls, value):
        from .functools._dispatch import UnionWidget

        annotations = []
        opt = dict(widget_type=UnionWidget, nullable=False, annotations=annotations)
        if isinstance(value, tuple):
            for val in value:
                if val is not None:
                    annotations.append(val)
                else:
                    opt["nullable"] = True
        else:
            raise TypeError("Union must be a tuple or a dict.")
        # union = Union[tuple(annotations)]  # type: ignore
        return Annotated[Any, opt]


class Union(metaclass=_UnionAlias):
    """
    Make Annotated type similar to ``typing.Union``.

    Arguments annotated with ``Union[int, str]`` will create a
    ``UnionWidget`` with a ``SpinBox`` and a ``LineEdit`` as inner widgets.

    >>> from magicclass import magicclass
    >>> from magicclass.types import Union

    >>> @magicclass
    >>> class A:
    >>>     def f(self, a: Union[int, str]):
    >>>         print(a)

    >>> ui = A()
    >>> ui.show()
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Union cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Union.")


# Stored type


class _StoredLastAlias(type):
    @overload
    def __getitem__(cls, value: type[_T]) -> type[_T]:
        ...

    @overload
    def __getitem__(cls, value: tuple[type[_T], Hashable]) -> type[_T]:
        ...

    def __getitem__(cls, value):
        stored_cls = Stored._class_getitem(value)

        def _getter(w=None):
            store = stored_cls._store
            if len(store) > 0:
                return store[-1]
            raise IndexError(f"Storage of {stored_cls} is empty.")

        return Annotated[
            stored_cls.__args__[0], {"bind": _getter, "widget_type": EmptyWidget}
        ]


class StoredLast(Generic[_T], metaclass=_StoredLastAlias):
    def __new__(cls, *args, **kwargs):
        raise TypeError("Type StoredLast cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.StoredLast.")


class _StoredMeta(type):
    _instances: dict[Hashable, _StoredMeta] = {}
    _categorical_widgets: defaultdict[Hashable, list[CategoricalWidget]] = defaultdict(
        list
    )

    _store: list
    _maxsize: int
    __args__: tuple[type]

    @overload
    def __getitem__(cls, value: type[_T]) -> type[_T]:
        ...

    @overload
    def __getitem__(cls, value: tuple[type[_T], Hashable]) -> type[_T]:
        ...

    def __getitem__(cls, value):
        return Stored._class_getitem(value)


class DefaultSpec:
    def __repr__(self) -> str:
        return "<default>"

    def __hash__(self) -> int:
        return id(self)


class Stored(Generic[_T], metaclass=_StoredMeta):
    """
    Use variable store of specific type.

    ``Stored[T]`` is identical to ``T`` for the type checker. However, outputs
    are stored for later use in functions with the same annotation.

    >>> from magicclass import magicclass
    >>> from magicclass.types import Stored

    >>> @magicclass
    >>> class A:
    ...     def f(self, a: int) -> Stored[str]:
    ...         return str(a)
    ...     def print_one_of_stored(self, a: Stored[str]):
    ...         print(a)

    If you want to use different storage for the same type, you can use any
    hashable specifier as the second argument.

    >>> @magicclass
    >>> class A:
    ...     def f0(self, a: int) -> Stored[str, 0]:
    ...         return str(a)
    ...     def f1(self, a: int) -> Stored[str, 1]:
    ...         return str(a)
    ...     def print_one_of_stored(self, a: Stored[str, 0], b: Stored[str, 1]):
    ...         print(a)
    """

    _store: list[_T]
    _maxsize: int
    _hash_value: Hashable
    Last = StoredLast
    _no_spec = DefaultSpec()

    __args__: tuple[type] = ()
    _repr_map: dict[type[_U], Callable[[_U], str]] = {}

    @classmethod
    def new(cls, tp: type[_U], maxsize: int | None = 12) -> Stored[_U]:
        """Create a new storage with given maximum size."""
        i = 0
        while (tp, i) in _StoredMeta._instances:
            i += 1
        outtype = Stored[tp, 0]
        if maxsize is None:
            outtype._maxsize = float("inf")
        else:
            if not isinstance(maxsize, int) or maxsize <= 0:
                raise TypeError("maxsize must be a positive integer")
            outtype._maxsize = maxsize
        return outtype

    @classmethod
    def hash_key(cls) -> tuple[type[_T], Hashable]:
        return cls.__args__[0], cls._hash_value

    @overload
    @classmethod
    def register_repr(
        self, tp: type[_U], func: Callable[[_U], str]
    ) -> Callable[[_U], str]:
        ...

    @overload
    @classmethod
    def register_repr(
        self, tp: type[_U]
    ) -> Callable[[Callable[[_U], str]], Callable[[_U], str]]:
        ...

    @classmethod
    def register_repr(self, tp, func=None):
        """Register a function to convert a value to string."""

        def wrapper(f):
            if not callable(f):
                raise TypeError("func must be a callable")
            self._repr_map[tp] = f
            return f

        return wrapper(func) if func is not None else wrapper

    @classmethod
    def _get_choice(cls, w: CategoricalWidget):
        # NOTE: cls is Stored, not Stored[X]!
        ann = w.annotation
        assert issubclass(ann, Stored), ann
        widgets = _StoredMeta._categorical_widgets[ann.hash_key()]
        if w not in widgets:
            widgets.append(w)
        _repr_func = cls._repr_map.get(ann.__args__[0], _repr_like)
        return [
            (f"{i}: {_repr_func(x)}", x) for i, x in enumerate(reversed(ann._store))
        ]

    @staticmethod
    def _store_value(gui: FunctionGui, value, return_type):
        assert issubclass(return_type, Stored), return_type
        return_type._store.append(value)
        if len(return_type._store) > return_type._maxsize:
            return_type._store.pop(0)

        # reset all the related categorical widgets.
        for w in _StoredMeta._categorical_widgets.get(return_type.hash_key(), []):
            w.reset_choices()

        # Callback of the inner type annotation
        from magicgui.type_map import type2callback

        inner_type = return_type.__args__[0]
        for cb in type2callback(inner_type):
            cb(gui, value, inner_type)

    @classmethod
    def _class_getitem(cls, value):
        if isinstance(value, tuple):
            if len(value) != 2:
                raise TypeError("Input of Stored must be a type or (type, Any)")
            _tp, _hash = value
        else:
            if not is_type_like(value):
                raise TypeError(
                    "The first argument of Stored must be a type but "
                    f"got {type(value)}."
                )
            _tp, _hash = value, cls._no_spec
        key = (_tp, _hash)
        if outtype := _StoredMeta._instances.get(key):
            return outtype
        name = f"Stored[{_tp.__name__}, {_hash!r}]"
        ns = {
            "_store": [],
            "_hash_value": _hash,
            "_maxsize": 12,
        }
        outtype: cls = _StoredMeta(name, (cls,), ns)
        outtype.__args__ = (_tp,)
        _StoredMeta._instances[key] = outtype
        return outtype


def _repr_like(x: Any):
    lines = repr(x).split("\n")
    if len(lines) == 1:
        return lines[0]
    else:
        return lines[0] + " ... "


def __getattr__(key: str):
    if key in ["List", "Tuple"]:
        import warnings

        warnings.warn(
            f"Type {key!r} is deprecated. Please use typing.{key}.",
            DeprecationWarning,
            stacklevel=2,
        )

        return getattr(typing, key)
    raise AttributeError(f"module {__name__!r} has no attribute {key!r}")
