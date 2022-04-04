from __future__ import annotations
from contextlib import contextmanager
from typing import Any, TYPE_CHECKING, Callable, TypeVar, overload, Generic, Union
from typing_extensions import Literal
from pathlib import Path
import datetime
import sys
from enum import Enum
from dataclasses import Field, MISSING
from magicgui.type_map import get_widget_class
from magicgui.widgets import create_widget
from magicgui.widgets._bases import Widget, ValueWidget
from magicgui.widgets._bases.value_widget import UNSET

from .gui.mgui_ext import Action, WidgetAction

if TYPE_CHECKING:
    from magicgui.widgets._protocols import WidgetProtocol
    from .gui._base import MagicTemplate
    from .gui.mgui_ext import AbstractAction

    _M = TypeVar("_M", bound=MagicTemplate)

if sys.version_info >= (3, 10):
    # From Python 3.10 the Field type takes an additional argument "kw_only".
    class Field(Field):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, kw_only=False)


_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V", bound=object)


class MagicField(Field, Generic[_W, _V]):
    """
    Field class for magicgui construction.


    This object is compatible with dataclass. MagicField object is in "ready for
    widget construction" state.
    """

    def __init__(
        self,
        default=MISSING,
        default_factory=MISSING,
        metadata: dict[str, Any] = {},
        name: str | None = None,
        record: bool = True,
    ):
        metadata = metadata.copy()
        if default is MISSING:
            default = metadata.pop("value", MISSING)
        super().__init__(
            default=default,
            default_factory=default_factory,
            init=True,
            repr=True,
            hash=False,
            compare=False,
            metadata=metadata,
        )
        self.callbacks: list[Callable] = []
        self.guis: dict[int, _M] = {}
        self.name = name
        self.record = record

        # MagicField has to remenber the first class that referred to itself so that it can
        # "know" the namespace it belongs to.
        self.parent_class: type = None

    def __repr__(self):
        return self.__class__.__name__.rstrip("Field") + super().__repr__()

    def copy(self) -> MagicField:
        """Copy object."""
        return self.__class__(
            self.default, self.default_factory, self.metadata, self.name, self.record
        )

    @contextmanager
    def _resolve_choices(self, obj: Any) -> dict[str, Any]:
        """If method is given as choices, get generate method from it."""
        from .gui._base import _is_instance_method, _method_as_getter

        _arg_choices = self.options.get("choices", None)
        if _is_instance_method(obj, _arg_choices):
            self.options["choices"] = _method_as_getter(obj, _arg_choices)
        try:
            yield self
        finally:
            if _arg_choices is not None:
                self.options["choices"] = _arg_choices

    def get_widget(self, obj: Any) -> _W:
        """
        Get a widget from ``obj``. This function will be called every time MagicField is referred
        by ``obj.field``.
        """
        obj_id = id(obj)
        objtype = type(obj)
        if obj_id in self.guis.keys():
            widget = self.guis[obj_id]
        else:
            with self._resolve_choices(obj):
                widget = self.to_widget()
                self.guis[obj_id] = widget
            if self.parent_class is None:
                self.parent_class = objtype

        return widget

    def get_action(self, obj: Any) -> AbstractAction:
        """
        Get an action from ``obj``. This function will be called every time MagicField is referred
        by ``obj.field``.
        """
        obj_id = id(obj)
        objtype = type(obj)
        if obj_id in self.guis.keys():
            action = self.guis[obj_id]
        else:
            with self._resolve_choices(obj):
                action = self.to_action()
                self.guis[obj_id] = action
            if self.parent_class is None:
                self.parent_class = objtype

        return action

    def as_getter(self, obj: Any) -> Callable[[Any], _V]:
        """Make a function that get the value of Widget or Action."""
        return lambda w: self.guis[id(obj)].value

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> MagicField[_W, _V] | _W:
        ...

    @overload
    def __get__(self, obj: Any, objtype=None) -> _W:
        ...

    def __get__(self, obj, objtype=None):
        """Get widget for the object."""
        if obj is None:
            return self
        return self.get_widget(obj)

    def __set__(self, obj, value) -> None:
        raise AttributeError(f"Cannot set value to {self.__class__.__name__}.")

    def ready(self) -> bool:
        return not self.not_ready()

    def not_ready(self) -> bool:
        if "widget_type" in self.metadata:
            return False
        return self.default is MISSING and self.default_factory is MISSING

    def to_widget(self) -> _W:
        """
        Create a widget from the field.

        Returns
        -------
        Widget
            Widget object that is ready to be inserted into Container.

        Raises
        ------
        ValueError
            If there is not enough information to build a widget.
        """
        if self.default_factory is not MISSING and issubclass(
            self.default_factory, Widget
        ):
            widget = self.default_factory(**self.options)
        else:
            widget = create_widget(
                value=self.value, annotation=self.annotation, **self.metadata
            )
        widget.name = self.name
        return widget

    def to_action(self) -> Action | WidgetAction[_W]:
        """
        Create a menu action or a menu widget action from the field.

        Returns
        -------
        Action or WidgetAction
            Object that can be added to menu.

        Raises
        ------
        ValueError
            If there is not enough information to build an action.
        """
        if type(self.default) is bool or self.default_factory is bool:
            # we should not use "isinstance" or "issubclass" because subclass may be mapped
            # to different widget by users.
            value = False if self.default is MISSING else self.default
            action = Action(
                checkable=True,
                checked=value,
                text=self.name.replace("_", " "),
                name=self.name,
            )
            options = self.metadata.get("options", {})
            for k, v in options.items():
                setattr(action, k, v)
        else:
            widget = self.to_widget()
            action = WidgetAction(widget)
        return action

    def connect(self, func: Callable) -> Callable:
        """Set callback function to "ready to connect" state."""
        if not callable(func):
            raise TypeError("Cannot connect non-callable object")
        self.callbacks.append(func)
        return func

    def disconnect(self, func: Callable) -> None:
        """
        Disconnect callback from the field.
        This method does NOT disconnect callbacks from widgets that are
        already created.
        """
        i = self.callbacks.index(func)
        self.callbacks.pop(i)
        return None

    def wraps(
        self,
        method: Callable | None = None,
        *,
        template: Callable | None = None,
        copy: bool = False,
    ):
        """
        Call the ``wraps`` class method of magic class.

        This method is needed when a child magic class is defined outside the main magic
        class, and integrated into the main magic class by ``field`` function, like below

        .. code-block:: python

            @magicclass
            class B:
                def func(self): ...  # pre-definition

            @magicclass
            class A:
                b = field(B)

                @b.wraps
                def func(self):
                    # do something

        Parameters
        ----------
        method : Callable, optional
            Method of parent class.
        template : Callable, optional
            Function template for signature.
        copy: bool, default is False
            If true, wrapped method is still enabled.

        Returns
        -------
        Callable
            Same method as input, but has updated signature.
        """
        from .gui._base import BaseGui

        cls = self.default_factory
        if not (isinstance(cls, type) and issubclass(cls, BaseGui)):
            raise TypeError(
                "The wraps method cannot be used for any objects but magic class."
            )
        return cls.wraps(method=method, template=template, copy=copy)

    @property
    def value(self) -> Any:
        return UNSET if self.default is MISSING else self.default

    @property
    def annotation(self):
        return None if self.default_factory is MISSING else self.default_factory

    @property
    def options(self) -> dict:
        return self.metadata.get("options", {})

    @property
    def widget_type(self) -> str:
        if self.default_factory is not MISSING and issubclass(
            self.default_factory, Widget
        ):
            wcls = self.default_factory
        else:
            wcls = get_widget_class(value=self.value, annotation=self.annotation)
        return wcls.__name__


class MagicValueField(MagicField[_W, _V]):
    """
    Field class for magicgui construction. Unlike MagicField, object of this class always
    returns value itself.
    """

    def get_widget(self, obj: Any) -> _W:
        widget = super().get_widget(obj)
        if not hasattr(widget, "value"):
            raise TypeError(
                "Widget is not a value widget or a widget with value: "
                f"{type(widget)}"
            )

        return widget

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> MagicValueField[_W, _V] | _V:
        ...

    @overload
    def __get__(self, obj: Any, objtype=None) -> _V:
        ...

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.get_widget(obj).value

    def __set__(self, obj: _M, value: _V) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        self.get_widget(obj).value = value


# magicgui symple types
_X = TypeVar(
    "_X",
    bound=Union[
        int,
        float,
        bool,
        str,
        Path,
        datetime.datetime,
        datetime.date,
        datetime.time,
        Enum,
        range,
        slice,
    ],
)


@overload
def field(
    obj: _X,
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[ValueWidget, _X]:
    ...


@overload
def field(
    obj: type[_W],
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_W, Any]:
    ...


@overload
def field(
    obj: type[_X],
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[ValueWidget, _X]:
    ...


@overload
def field(
    obj: type[_M],
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_M, Any]:
    ...


@overload
def field(
    obj: Any,
    *,
    name: str = "",
    widget_type: type[_W] = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_W, Any]:
    ...


@overload
def field(
    obj: Any,
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[Widget, Any]:
    ...


def field(
    obj: Any = MISSING,
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[Widget, Any]:
    """
    Make a MagicField object.

    >>> i = field(1)
    >>> i = field(widget_type="Slider")

    Parameters
    ----------
    obj : Any, default is MISSING
        Reference to determine what type of widget will be created. If Widget subclass is given,
        it will be used as is. If other type of class is given, it will used as type annotation.
        If an object (not type) is given, it will be assumed to be the default value.
    name : str, default is ""
        Name of the widget.
    widget_type : str, optional
        Widget type. This argument will be sent to ``create_widget`` function.
    options : WidgetOptions, optional
        Widget options. This parameter will always be used in ``widget(**options)`` form.
    record : bool, default is True
        Record value changes as macro.

    Returns
    -------
    MagicField
    """
    return _get_field(obj, name, widget_type, options, record, MagicField)


@overload
def vfield(
    obj: _X,
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[ValueWidget, _X]:
    ...


@overload
def vfield(
    obj: type[_W],
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[_W, Any]:
    ...


@overload
def vfield(
    obj: type[_X],
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[ValueWidget, _X]:
    ...


@overload
def vfield(
    obj: Any,
    *,
    name: str = "",
    widget_type: type[_W] = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[_W, Any]:
    ...


@overload
def vfield(
    obj: Any,
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[Widget, Any]:
    ...


def vfield(
    obj: Any = MISSING,
    *,
    name: str = "",
    widget_type: str | type[WidgetProtocol] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[Widget, Any]:
    """
    Make a MagicValueField object.

    >>> i = vfield(1)
    >>> i = vfield(widget_type="Slider")

    Unlike MagicField, value itself can be accessed.

    >>> ui.i      # int is returned
    >>> ui.i = 3  # set value to the widget.

    Parameters
    ----------
    obj : Any, default is MISSING
        Reference to determine what type of widget will be created. If Widget subclass is given,
        it will be used as is. If other type of class is given, it will used as type annotation.
        If an object (not type) is given, it will be assumed to be the default value.
    name : str, default is ""
        Name of the widget.
    widget_type : str, optional
        Widget type. This argument will be sent to ``create_widget`` function.
    options : WidgetOptions, optional
    record : bool, default is True
        Record value changes as macro.

    Returns
    -------
    MagicValueField
    """
    return _get_field(obj, name, widget_type, options, record, MagicValueField)


def _get_field(
    obj,
    name: str,
    widget_type: str | type[WidgetProtocol] | None,
    options: dict[str, Any],
    record: bool,
    field_class: type[MagicField],
) -> type[MagicField]:
    if not isinstance(options, dict):
        raise TypeError(f"Field options must be a dict, got {type(options)}")
    options = options.copy()
    metadata = dict(widget_type=widget_type, options=options)
    if "name" in options.keys():
        name = options["name"]
    kwargs = dict(metadata=metadata, name=name, record=record)
    if isinstance(obj, type):
        f = field_class(default_factory=obj, **kwargs)
    elif obj is MISSING:
        f = field_class(**kwargs)
    else:
        f = field_class(default=obj, **kwargs)

    return f
