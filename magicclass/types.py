from __future__ import annotations

from enum import Enum
import typing
from typing import Any, Union, Iterable
from typing_extensions import Literal, Annotated, _AnnotatedAlias

try:
    from typing import _tp_cache
except ImportError:

    def _tp_cache(x):
        return x


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

Color = Union[str, Iterable[float]]


class Bound:
    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Bound cannot be instantiated.")

    @_tp_cache
    def __class_getitem__(cls, value) -> _AnnotatedAlias:
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

        if isinstance(value, tuple):
            raise TypeError(
                "Bound[...] should be used with only one "
                "argument (the object to be bound)."
            )
        return Annotated[Any, {"bind": value}]

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Bound")


class Optional:
    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Bound cannot be instantiated.")

    @_tp_cache
    def __class_getitem__(cls, value) -> _AnnotatedAlias:
        if isinstance(value, tuple):
            type_, options = value
        else:
            type_, options = value, {}

        if not isinstance(type_, type):
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

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Optional")
