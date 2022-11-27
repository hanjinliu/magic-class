from __future__ import annotations
from contextlib import contextmanager
from functools import wraps, cached_property
import weakref
import types
from typing import (
    Any,
    TYPE_CHECKING,
    Callable,
    Iterator,
    TypeVar,
    overload,
)
from abc import ABCMeta
from magicgui.widgets import Container
from magicgui.widgets._bases import Widget
from psygnal import SignalInstance

from ._fields import MagicField, MagicValueField, _FieldObject
from ._define import define_callback, define_callback_gui
from magicclass.utils import Tooltips

if TYPE_CHECKING:
    from typing_extensions import Self, Literal


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
        _tooltips = Tooltips(cls)
        _fields: dict[str, MagicField] = {}
        for base in cls.__mro__[1:-1]:
            if type(base) is _FieldGroupMeta:
                _fields.update(base._fields)

        for k, v in namespace.items():
            if isinstance(v, _FieldObject):
                if k in _View._METHODS:
                    raise ValueError(f"Attribute {k} cannot be used in HasFields.")
                _fields[k] = v
                if not v.tooltip:
                    v.tooltip = _tooltips.attributes.get(k, "")

        cls._fields = types.MappingProxyType(_fields)

        return cls


_C = TypeVar("_C", bound=type)


@overload
def dataclass_gui(
    cls: _C,
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
) -> _C | type[HasFields]:
    ...


@overload
def dataclass_gui(
    cls: Literal[None],
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
) -> Callable[[_C], _C | type[HasFields]]:
    ...


def dataclass_gui(
    cls=None,
    /,
    *,
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=False,
):
    """
    A dataclass-like decorator for GUI-implemented class.

    .. code-block:: python

        @dataclass_gui
        class A:
            i: int = vfield(int)
            s: str = vfield(str)

    is identical to:

    .. code-block:: python

        @dataclass
        class A(HasFields):
            i: int = vfield(int)
            s: str = vfield(str)

    Returns
    -------
    HasField subtype
        GUI implemented class
    """

    def _wrapper(cls: type):
        from dataclasses import dataclass, Field, MISSING

        cls_annot = cls.__dict__.get("__annotations__", {})
        namespace: dict[str, Any] = {key: cls.__dict__[key] for key in cls_annot}
        newtype = type(cls.__name__, (cls, HasFields), namespace)
        if init:
            import inspect

            params: list[inspect.Parameter] = []
            _empty = inspect.Parameter.empty
            for name, annot in cls_annot.items():
                default = newtype.__dict__.get(name, _empty)
                if isinstance(default, MagicValueField):
                    default = default.value
                elif isinstance(default, Field):
                    default = default.default
                    if default is MISSING:
                        default = _empty

                param = inspect.Parameter(
                    name=name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=default,
                    annotation=annot,
                )
                params.append(param)

            signature = inspect.Signature(params)
            has_post_init = hasattr(newtype, "__post_init__")

            def __init__(self: HasFields, *args, **kwargs):
                bound = signature.bind(*args, **kwargs)
                with self.signals.blocked():
                    for k, v in bound.arguments.items():
                        setattr(self, k, v)
                if has_post_init:
                    self.__post_init__()

            __init__.__annotations__ = {p: p.annotation for p in params}
            __init__.__annotations__["return"] = None

            cls.__init__ = __init__

        if repr:

            def __repr__(self: HasFields) -> str:
                _repr = ", ".join(
                    f"{name}={getattr(self, name)!r}" for name in cls_annot
                )
                return f"{self.__class__.__name__}({_repr})"

            cls.__repr__ = __repr__

        return dataclass(
            newtype,
            init=False,
            repr=False,
            eq=eq,
            order=order,
            unsafe_hash=unsafe_hash,
            frozen=frozen,
        )

    return _wrapper if cls is None else _wrapper(cls)


class HasFields(metaclass=_FieldGroupMeta):
    """
    A trait implemented with widgets and signals.

    Subclasses can easily handle widgets and their value-change signals using
    the same attribute names.

    >>> class A(HasFields):
    >>>     a = vfield(int)
    >>>     b = vfield(str)
    >>> ins = A()
    >>> ins.a  # type: int
    >>> ins.widgets.a  # type: SpinBox
    >>> ins.signals.a  # type: SignalInstance

    """

    @cached_property
    def widgets(self) -> WidgetView:
        """Return a view of widgets."""
        return WidgetView(self)

    @cached_property
    def signals(self) -> SignalView:
        """Return a view of signals."""
        return SignalView(self)

    def __repr__(self) -> str:
        """List up child widgets."""
        _repr = ",\n\t".join(
            f"{name} = {wdt!r}" for name, wdt in self.widgets.iteritems()
        )
        return f"{self.__class__.__name__}(\n\t{_repr}\n)"


# NOTE: Typing of FieldGroup is tricky. When it is referred to via __get__, it
# must return a object of same type as itself to guarantee the child fields are
# also defined there. Thus, FieldGroup must inherit magicgui Container although
# the original container will never be used.
class FieldGroup(Container, HasFields, _FieldObject):
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
        self._containers: dict[int, Self] = {}
        self._callbacks: list[Callable] = []

    def __init_subclass__(cls) -> None:
        if "__init__" not in cls.__dict__.keys():
            return

        cls.__base_init__ = cls.__init__

        @wraps(cls.__init__)
        def __init__(self: cls, *args, **kwargs):
            self.__input_arguments = (args, kwargs)
            cls.__base_init__(self, *args, **kwargs)

        def __newlike__(self):
            args, kwargs = self.__input_arguments
            return cls(*args, **kwargs)

        cls.__init__ = __init__
        cls.__newlike__ = __newlike__

    def __newlike__(self) -> Self:
        """
        Make a copy of a FieldGroup.

        This method needs override if __init__ is overrided in a subclass.
        """
        return self.__class__(
            layout=self.layout,
            labels=self.labels,
            label=self.label,
            enabled=self.enabled,
            name=self.name,
            tooltip=self.tooltip,
        )

    def __set_name__(self, owner: type, name: str):
        """Set variable name as the container's name."""
        # self._parent_class = owner
        if self.name is None:
            self.name = name

    # Unlike Container, `self.x = value` should be allowed because `x` can be a value field.
    __setattr__ = object.__setattr__

    def copy(self) -> Self:
        """Copy widget."""
        wdt = self.__newlike__()
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
            from .._gui import MagicTemplate

            wdt = self.copy()
            self._containers[_id] = wdt
            if isinstance(obj, MagicTemplate):
                _def = define_callback_gui
            else:
                _def = define_callback
            for callback in self._callbacks:
                wdt.changed.connect(_def(obj, callback))
        return wdt

    def connect(self, callback: Callable):
        # self.changed.connect(callback)  NOTE: the original container doesn't need signals!
        self._callbacks.append(callback)
        return callback


class _View:
    _METHODS = (
        "iternames",
        "iterwidgets",
        "itersignals",
    )

    def __init__(self, obj: HasFields):
        self._obj_ref = weakref.ref(obj)

    def __repr__(self) -> str:
        _it = zip(self.iternames(), self.iterwidgets())
        _repr = ",\n\t".join(f"{name} = {repr(wdt)}" for name, wdt in _it)
        return f"{self.__class__.__name__}(\n\t{_repr}\n)"

    def __len__(self) -> int:
        obj = self._obj_ref()
        return len(obj.__class__._fields)

    def iternames(self) -> Iterator[str]:
        """Iterate widget names."""
        return iter(self._obj_ref().__class__._fields.keys())

    def iterwidgets(self) -> Iterator[Widget]:
        """Iterate widgets."""
        obj = self._obj_ref()
        for fld in obj.__class__._fields.values():
            wdt = fld.get_widget(obj)
            yield wdt

    def itersignals(self, skip_undef: bool = False) -> Iterator[SignalInstance | None]:
        """Iterate value-changed signals."""
        obj = self._obj_ref()
        for fld in obj.__class__._fields.values():
            wdt = fld.get_widget(obj)
            sig = getattr(wdt, "changed", None)
            if isinstance(sig, SignalInstance):
                yield sig
            elif not skip_undef:
                yield None


class WidgetView(_View):
    """View of widgets."""

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

    def iteritems(self) -> Iterator[tuple[str, Widget]]:
        """Iterate widget names and widgets themselves."""
        return iter(zip(self.iternames(), self.iterwidgets()))

    def __iter__(self) -> Iterator[Widget]:
        """Iterate widgets."""
        return self.iterwidgets()

    def as_container(
        self,
        layout: str = "vertical",
        labels: bool = True,
        keys: list[str] | None = None,
        **kwargs,
    ) -> Container:
        """Convert view into a Container widget."""
        if keys is None:
            widgets = list(self)
        else:
            widgets = [getattr(self, name) for name in keys]
        return Container(layout=layout, widgets=widgets, labels=labels, **kwargs)

    def show(self, run=False):
        """Create a container and show it."""
        return self.as_container().show(run=run)

    def emit_all(self) -> None:
        """Emit all the signals with current value."""
        for wdt, sig in zip(self.iterwidgets(), self.itersignals()):
            if sig is not None:
                sig.emit(wdt.value)


class SignalView(_View):
    """View of signals."""

    def __getattr__(self, name: str) -> SignalInstance:
        obj = self._obj_ref()
        fld = obj.__class__._fields.get(name, None)
        if isinstance(fld, _FieldObject):
            wdt = fld.get_widget(obj)
            sig = getattr(wdt, "changed", None)
            if not isinstance(sig, SignalInstance):
                raise AttributeError(f"Widget {wdt!r} does not have 'changed' signal")
            return sig
        raise AttributeError(f"{obj!r} does not have attribute {name!r}.")

    def __getitem__(self, key: str | int) -> SignalInstance:
        """Similar to list.__getitem__."""
        if isinstance(key, int):
            obj = self._obj_ref()
            key = list(obj.__class__._fields.keys())[key]
        try:
            wdt = self.__getattr__(key)
        except AttributeError:
            raise KeyError(key)
        return wdt

    def iteritems(self) -> Iterator[tuple[str, SignalInstance | None]]:
        """Iterate widget names and value-changed signals."""
        return iter(zip(self.iternames(), self.itersignals()))

    def __iter__(self) -> Iterator[SignalInstance | None]:
        return self.itersignals()

    def block(self) -> None:
        """Block all the signals."""
        for sig in self.itersignals(skip_undef=True):
            sig.block()

    def unblock(self) -> None:
        """Unblock all the signals."""
        for sig in self.itersignals(skip_undef=True):
            sig.unblock()

    @contextmanager
    def blocked(self):
        """Temporarly block all signals."""
        self.block()
        try:
            yield
        finally:
            self.unblock()
