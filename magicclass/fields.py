from __future__ import annotations
from contextlib import contextmanager
import weakref
from typing import (
    Any,
    TYPE_CHECKING,
    Callable,
    Iterator,
    TypeVar,
    overload,
    Generic,
    Union,
)
from abc import ABCMeta
from typing_extensions import Literal, _AnnotatedAlias
from pathlib import Path
import datetime
import sys
from enum import Enum
from dataclasses import Field, MISSING
from magicgui.type_map import get_widget_class
from magicgui.widgets import create_widget, Container
from magicgui.widgets._bases import Widget, ValueWidget, ContainerWidget
from magicgui.widgets._bases.value_widget import UNSET

from ._gui.mgui_ext import Action, WidgetAction

if TYPE_CHECKING:
    from magicgui.widgets._protocols import WidgetProtocol
    from typing_extensions import Self
    from ._gui._base import MagicTemplate
    from ._gui.mgui_ext import AbstractAction

    _M = TypeVar("_M", bound=MagicTemplate)

if sys.version_info >= (3, 10):
    # From Python 3.10 the Field type takes an additional argument "kw_only".
    class Field(Field):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, kw_only=False)

    from typing import _BaseGenericAlias

else:
    from typing_extensions import _BaseGenericAlias


class _FieldObject:
    name: str

    def get_widget(self, obj: Any) -> Widget:
        raise NotImplementedError()


_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V", bound=object)


class MagicField(Field, _FieldObject, Generic[_W, _V]):
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
        self._callbacks: list[Callable] = []
        self._guis: dict[int, _M] = {}
        self.name = name
        self._record = record

        # MagicField has to remenber the first class that referred to itself so that it can
        # "know" the namespace it belongs to.
        self._parent_class: type | None = None

    def __repr__(self):
        return self.__class__.__name__.rstrip("Field") + super().__repr__()

    def __set_name__(self, owner: type, name: str) -> None:
        super().__set_name__(owner, name)
        self._parent_class = owner
        if self.name is None:
            self.name = name

    @property
    def callbacks(self) -> tuple[Callable, ...]:
        """Return callbacks in an immutable way."""
        return tuple(self._callbacks)

    @property
    def record(self) -> bool:
        return self._record

    def copy(self) -> MagicField:
        """Copy object."""
        return self.__class__(
            self.default, self.default_factory, self.metadata, self.name, self._record
        )

    @contextmanager
    def _resolve_choices(self, obj: Any) -> dict[str, Any]:
        """If method is given as choices, get generate method from it."""
        from ._gui._base import _is_instance_method, _method_as_getter

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
        from ._gui import MagicTemplate

        obj_id = id(obj)
        if obj_id in self._guis.keys():
            widget = self._guis[obj_id]
        else:
            with self._resolve_choices(obj):
                widget = self.to_widget()
                self._guis[obj_id] = widget

            if isinstance(widget, (ValueWidget, ContainerWidget)):
                if isinstance(obj, MagicTemplate):
                    _def = _define_callback_gui
                else:
                    _def = _define_callback
                for callback in self._callbacks:
                    # funcname = callback.__name__
                    widget.changed.connect(_def(obj, callback))

        return widget

    def get_action(self, obj: Any) -> AbstractAction:
        """
        Get an action from ``obj``. This function will be called every time MagicField is referred
        by ``obj.field``.
        """
        from ._gui import MagicTemplate

        obj_id = id(obj)
        if obj_id in self._guis.keys():
            action = self._guis[obj_id]
        else:
            with self._resolve_choices(obj):
                action = self.to_action()
                self._guis[obj_id] = action

            if action.support_value:
                if isinstance(obj, MagicTemplate):
                    _def = _define_callback_gui
                else:
                    _def = _define_callback
                for callback in self._callbacks:
                    # funcname = callback.__name__
                    action.changed.connect(_def(obj, callback))

        return action

    def as_getter(self, obj: Any) -> Callable[[Any], _V]:
        """Make a function that get the value of Widget or Action."""
        return lambda w: self._guis[id(obj)].value

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
        if self.default_factory is not MISSING and _is_subclass(
            self.default_factory, Widget
        ):
            widget = self.default_factory(**self.options)
        else:
            if "annotation" not in self.metadata.keys():
                widget = create_widget(
                    value=self.value, annotation=self.annotation, **self.metadata
                )
            else:
                widget = create_widget(value=self.value, **self.metadata)
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
        self._callbacks.append(func)
        return func

    def disconnect(self, func: Callable) -> None:
        """
        Disconnect callback from the field.
        This method does NOT disconnect callbacks from widgets that are
        already created.
        """
        i = self._callbacks.index(func)
        self._callbacks.pop(i)
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
        from ._gui._base import BaseGui

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
        if self.default_factory is not MISSING and _is_subclass(
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
        list,
        tuple,
    ],
)


@overload
def field(
    obj: _X,
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[ValueWidget, _X]:
    ...


@overload
def field(
    obj: type[_W],
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_W, Any]:
    ...


@overload
def field(
    obj: type[_X],
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[ValueWidget, _X]:
    ...


@overload
def field(
    obj: type[_M],
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_M, Any]:
    ...


@overload
def field(
    obj: Any,
    *,
    name: str | None = None,
    widget_type: type[_W] = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_W, Any]:
    ...


@overload
def field(
    obj: Any,
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[Widget, Any]:
    ...


def field(
    obj: Any = MISSING,
    *,
    name: str | None = None,
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
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[ValueWidget, _X]:
    ...


@overload
def vfield(
    obj: type[_W],
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[_W, Any]:
    ...


@overload
def vfield(
    obj: type[_X],
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[ValueWidget, _X]:
    ...


@overload
def vfield(
    obj: Any,
    *,
    name: str | None = None,
    widget_type: type[_W] = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[_W, Any]:
    ...


@overload
def vfield(
    obj: Any,
    *,
    name: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[Widget, Any]:
    ...


def vfield(
    obj: Any = MISSING,
    *,
    name: str | None = None,
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
) -> MagicField:
    if not isinstance(options, dict):
        raise TypeError(f"Field options must be a dict, got {type(options)}")
    options = options.copy()
    metadata = dict(widget_type=widget_type, options=options)
    name = options.get("name", name)
    kwargs = dict(metadata=metadata, name=name, record=record)
    if isinstance(obj, (type, _BaseGenericAlias)):
        if isinstance(obj, _AnnotatedAlias):
            from magicgui.signature import split_annotated_type

            _, widget_option = split_annotated_type(obj)
            kwargs["metadata"].update(widget_option)
        f = field_class(default_factory=obj, **kwargs)
    elif obj is MISSING:
        f = field_class(**kwargs)
    else:
        f = field_class(default=obj, **kwargs)

    return f


def _is_subclass(obj: Any, class_or_tuple):
    try:
        return issubclass(obj, class_or_tuple)
    except Exception:
        return False


def _define_callback(self: Any, callback: Callable):
    def _callback():
        callback(self)
        return None

    return _callback


def _define_callback_gui(self: MagicTemplate, callback: Callable):
    """Define a callback function from a method."""

    *_, clsname, funcname = callback.__qualname__.split(".")
    mro = self.__class__.__mro__
    for base in mro:
        if base.__name__ == clsname:

            def _callback():
                with self.macro.blocked():
                    getattr(base, funcname)(self)
                return None

            break
    else:

        def _callback():
            # search for parent instances that have the same name.
            current_self = self
            while not (
                hasattr(current_self, funcname)
                and current_self.__class__.__name__ == clsname
            ):
                current_self = current_self.__magicclass_parent__
            with self.macro.blocked():
                getattr(current_self, funcname)()
            return None

    return _callback


class _FieldGroupMeta(ABCMeta):
    _fields: dict[str, MagicField]

    def __new__(
        fcls: type,
        name: str,
        bases: tuple,
        namespace: dict,
        **kwds,
    ) -> _FieldGroupMeta:
        cls: _FieldGroupMeta = type.__new__(fcls, name, bases, namespace, **kwds)
        _fields: dict[str, MagicField] = {}
        for k, v in namespace.items():
            if isinstance(v, _FieldObject):
                _fields[k] = v

        cls._fields = _fields

        return cls


class HasFields(metaclass=_FieldGroupMeta):
    """Base class with _FieldGroupMeta as the meta-class."""

    @property
    def widgets(self):
        """Return a view of widgets."""
        return WidgetView(self)

    def __repr__(self) -> str:
        """List up child widgets."""
        _repr = ",\n\t".join(
            f"{name} = {repr(wdt)}" for name, wdt in self.widgets.iteritems()
        )
        return f"{self.__class__.__name__}(\n\t{_repr}\n)"


# NOTE: Typing of FieldGroup is tricky. When it is referred to via __get__, it must return
# a object of same type as itself to guarantee the child fields are also defined there.
# Thus, FieldGroup must inherit magicgui Container although the original container will
# never be used.
class FieldGroup(Container, HasFields, _FieldObject):
    _containers: dict[int, Self] = {}

    def __init__(
        self,
        layout: str = "vertical",
        labels: bool = True,
        name: str | None = None,
        **kwargs,
    ):
        widgets = [fld.get_widget(self) for fld in self.__class__._fields.values()]
        super().__init__(
            layout=layout, widgets=widgets, labels=labels, name=name, **kwargs
        )
        self._callbacks = []

    def __set_name__(self, owner: type, name: str):
        # self._parent_class = owner
        if self.name is None:
            self.name = name

    # Unlike Container, `self.x = value` should be allowed because `x` can be a value field.
    __setattr__ = object.__setattr__

    def copy(self) -> Self:
        """Copy widget."""
        wdt = self.__class__(
            layout=self.layout,
            labels=self.labels,
            label=self.label,
            enabled=self.enabled,
            name=self.name,
            tooltip=self.tooltip,
        )
        for callback in self._callbacks:
            wdt.connect(callback)
        return wdt

    @property
    def callbacks(self) -> tuple[Callable, ...]:
        """Return callbacks in an immutable way."""
        return tuple(self._callbacks)

    @overload
    def __get__(self, obj: Literal[None], objtype: Any | None = None) -> Self:
        ...

    @overload
    def __get__(self, obj: Any, objtype: Any | None = None) -> Self:
        ...

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.get_widget(obj)

    def __set__(self, obj, value) -> None:
        raise AttributeError(f"Cannot set value to {self.__class__.__name__}.")

    def get_widget(self, obj) -> Container:
        _id = id(obj)
        wdt = self._containers.get(_id, None)
        if wdt is None:
            wdt = self.copy()
            self._containers[_id] = wdt
        return wdt

    def connect(self, callback: Callable):
        # self.changed.connect(callback)  NOTE: the original container doesn't need signals!
        self._callbacks.append(callback)
        return callback


class WidgetView:
    """View of widgets."""

    def __init__(self, obj: HasFields):
        self._obj_ref = weakref.ref(obj)

    def __repr__(self) -> str:
        _repr = ",\n\t".join(f"{name} = {repr(wdt)}" for name, wdt in self.iteritems())
        return f"{self.__class__.__name__}(\n\t{_repr}\n)"

    def __getattr__(self, name: str) -> Widget:
        obj = self._obj_ref()
        fld = obj.__class__._fields.get(name, None)
        if isinstance(fld, _FieldObject):
            return fld.get_widget(obj)
        raise AttributeError(f"{obj!r} does not have attribute {name!r}.")

    def __getitem__(self, key: str | int) -> Widget:
        """Similar to Container's __getitem__."""
        if isinstance(key, int):
            obj = self._obj_ref()
            key = list(obj.__class__._fields.keys())[key]
        try:
            wdt = self.__getattr__(key)
        except AttributeError:
            raise KeyError(key)
        return wdt

    def iternames(self) -> Iterator[str]:
        """Iterate widget names."""
        return iter(self._obj_ref().__class__._fields.keys())

    def iterwidgets(self) -> Iterator[Widget]:
        """Iterate widgets."""
        obj = self._obj_ref()
        for fld in obj.__class__._fields.values():
            wdt = fld.get_widget(obj)
            yield wdt

    def iteritems(self) -> Iterator[tuple[str, Widget]]:
        """Iterate widget names and widgets themselves."""
        return iter(zip(self.iternames(), self.iterwidgets()))

    def __iter__(self) -> Iterator[Widget]:
        """Iterate widgets."""
        return self.iterwidgets()

    def as_container(self, layout="vertical", labels=True, **kwargs) -> Container:
        """Convert view into a Container widget."""
        widgets = list(self)
        return Container(layout=layout, widgets=widgets, labels=labels, **kwargs)
