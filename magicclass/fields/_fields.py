from __future__ import annotations
import inspect
from types import GeneratorType
from typing import (
    Any,
    TYPE_CHECKING,
    Callable,
    Sequence,
    TypeVar,
    overload,
    Generic,
)
from typing_extensions import Literal
import threading
from timeit import default_timer
from functools import wraps
import warnings
from magicgui.widgets import create_widget, Widget
from magicgui.widgets.bases import (
    ValueWidget,
    ContainerWidget,
    CategoricalWidget,
)
from magicgui.types import Undefined
from magicclass.types import MGUI_SIMPLE_TYPES

from ._define import define_callback, define_callback_gui

from magicclass.utils import (
    is_instance_method,
    method_as_getter,
    eval_attribute,
    is_type_like,
)
from magicclass.signature import (
    MagicMethodSignature,
    is_annotated,
    split_annotated_type,
)
from magicclass._gui.mgui_ext import Action, WidgetAction
from magicclass._exceptions import Aborted

if TYPE_CHECKING:
    from typing_extensions import Self, ParamSpec
    from superqt.utils import WorkerBase
    from magicclass.utils import thread_worker
    from magicclass._gui._base import MagicTemplate
    from magicclass._gui.mgui_ext import AbstractAction

    _M = TypeVar("_M", bound=MagicTemplate)
    _X = TypeVar("_X", bound=MGUI_SIMPLE_TYPES)
    _P = ParamSpec("_P")


class _FieldObject:
    name: str
    tooltip: str

    def get_widget(self, obj: Any) -> Widget:
        raise NotImplementedError()


_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V")
_U = TypeVar("_U")
_F = TypeVar("_F", bound=Callable)


class MagicField(_FieldObject, Generic[_W]):
    """
    Field class for magicgui construction.

    This object is compatible with dataclass. MagicField object is in "ready for
    widget construction" state.
    """

    default_object = object()

    def __init__(
        self,
        value: Any = Undefined,
        name: str | None = None,
        label: str | None = None,
        annotation: Any = None,
        widget_type: type | str | None = None,
        options: dict[str, Any] | None = None,
        record: bool = True,
        constructor: Callable[[Any], Widget] | None = None,
    ):
        if options is None:
            options = {}
        if value is Undefined:
            value = options.pop("value", Undefined)

        if constructor is None:

            def _create_widget(obj):
                return create_widget(
                    self.value,
                    name=self.name or "",
                    label=self.label or "",
                    annotation=self.annotation,
                    widget_type=self.widget_type,
                    options=self.options,
                )

            constructor = _create_widget

        self.value = value
        self.name = name
        self.label = label
        self.annotation = annotation
        self.options = options
        self._widget_type = widget_type
        self._constructor = constructor
        self._callbacks: list[Callable] = []
        self._guis: dict[int, _M] = {}
        self._record = record

        # MagicField has to remenber the first class that referred to itself so
        # that it can "know" the namespace it belongs to.
        self._parent_class: type | None = None

        # This attribute will be used when wrapped field/vfield is used.
        self._destination_class: type | None = None

    def __repr__(self):
        attrs = ["value", "name", "widget_type", "record", "options"]
        kw = ", ".join(f"{a}={getattr(self, a)!r}" for a in attrs)
        return f"{self.__class__.__name__}({kw})"

    def __set_name__(self, owner: type, name: str) -> None:
        self._parent_class = owner
        if name in getattr(owner, "__annotations__", {}) and self.annotation is None:
            self.annotation = owner.__annotations__[name]
        if self.name is None:
            self.name = name

        if self._destination_class is not None:
            from magicclass.wrappers import abstractapi

            api = getattr(self._destination_class, name, None)
            if isinstance(api, abstractapi):
                api.resolve()
                api.__signature__ = MagicMethodSignature([])

    def set_destination(self, dest: type) -> None:
        self._destination_class = dest
        return None

    def with_options(
        self,
        value: Any = Undefined,
        tooltip: str = Undefined,
        visible: bool = Undefined,
        enabled: bool = Undefined,
        gui_only: bool = Undefined,
        bind=Undefined,
        **kwargs,
    ) -> Self:
        """
        Method ot add options to the field.

        Following expressions returns the same field.
        >>> x = field(int, options={"max": 10})
        >>> x = field(int).with_options(max=10)
        """
        kwargs = dict(
            value=value,
            tooltip=tooltip,
            visible=visible,
            enabled=enabled,
            gui_only=gui_only,
            bind=bind,
            **kwargs,
        )
        to_pop: list[str] = []
        for k, v in kwargs.items():
            if v is Undefined:
                to_pop.append(k)
        for k in to_pop:
            kwargs.pop(k)
        if "value" in kwargs:
            self.value = kwargs.pop("value")
        self.options.update(kwargs)
        return self

    @overload
    def with_choices(
        self, choices: Sequence[tuple[str, _U]]
    ) -> MagicField[CategoricalWidget[_U]]:
        ...

    @overload
    def with_choices(self, choices: Sequence[_U]) -> MagicField[CategoricalWidget[_U]]:
        ...

    @overload
    def with_choices(
        self, choices: Callable[..., Sequence[tuple[str, _U]]]
    ) -> MagicField[CategoricalWidget[_U]]:
        ...

    @overload
    def with_choices(
        self, choices: Callable[..., Sequence[_U]]
    ) -> MagicField[CategoricalWidget[_U]]:
        ...

    def with_choices(self, choices):
        """Method to add choices to the field."""
        self.options["choices"] = choices
        return self

    def with_widget_type(self, widget_type: type[Widget]):
        """Method to add widget type to the field."""
        self._widget_type = widget_type
        return self

    @property
    def __signature__(self):
        """This property is necessary to hack _unwrap_method."""
        additional_options = {}
        if self._destination_class is not None:
            additional_options["into"] = self._destination_class.__name__
        return MagicMethodSignature([], additional_options=additional_options)

    @property
    def constructor(self) -> Callable[[Any], Widget]:
        """Get widget constructor."""
        return self._constructor

    @property
    def callbacks(self) -> tuple[Callable, ...]:
        """Return callbacks in an immutable way."""
        return tuple(self._callbacks)

    @property
    def record(self) -> bool:
        return self._record

    def construct(self, obj) -> _W:
        """Construct a widget."""
        constructor = self.constructor
        _arg_choices = self.options.get("choices", None)
        if isinstance(_arg_choices, str):
            _arg_choices = eval_attribute(type(obj), _arg_choices)

        if is_instance_method(_arg_choices):
            self.options["choices"] = method_as_getter(obj, _arg_choices)
        try:
            if _is_magicclass(constructor):
                widget = constructor(**self.options)
            else:
                widget = constructor(obj)
                if not isinstance(widget, Widget):
                    raise TypeError(
                        f"{self.__class__.__name__} {self.name} created non-widget "
                        f"object {type(widget)}."
                    )

        finally:
            if _arg_choices is not None:
                self.options["choices"] = _arg_choices

        return widget

    def copy(self) -> MagicField[_W]:
        """Copy object."""
        return self.__class__(
            value=self.value,
            name=self.name,
            label=self.label,
            annotation=self.annotation,
            widget_type=self.widget_type,
            options=self.options,
            record=self.record,
            constructor=self.constructor,
        )

    @classmethod
    def from_callable(cls, func: Callable[..., _W]) -> Self[_W, Any]:
        """Use a function as the constructor of MagicField."""
        return cls(constructor=func)

    def get_widget(self, obj: Any) -> _W:
        """
        Get a widget from ``obj``.

        This function will be called every time MagicField is referred by
        ``obj.field``.
        """
        obj_id = id(obj)
        if (widget := self._guis.get(obj_id, None)) is None:
            self._guis[obj_id] = widget = self.construct(obj)
            widget.name = self.name or ""

            if isinstance(widget, (ValueWidget, ContainerWidget)):
                _def = self._get_define_callback(obj)
                for callback in self._callbacks:
                    widget.changed.connect(_def(obj, callback))

        return widget

    def get_action(self, obj: Any) -> AbstractAction:
        """
        Get an action from ``obj``. This function will be called every time MagicField is referred
        by ``obj.field``.
        """
        obj_id = id(obj)
        if obj_id in self._guis.keys():
            action = self._guis[obj_id]
        else:
            if type(self.value) is bool or self.annotation is bool:
                # we should not use "isinstance" or "issubclass" because subclass
                # may be mapped to different widget by users.
                value = False if self.value is Undefined else self.value
                action = Action(
                    checkable=True,
                    checked=value,
                    text=self.name.replace("_", " "),
                    name=self.name,
                )
                for k, v in self.options.items():
                    setattr(action, k, v)
            else:
                widget = self.construct(obj)
                widget.name = self.name
                action = WidgetAction(widget)

            self._guis[obj_id] = action

            if action.support_value:
                _def = self._get_define_callback(obj)
                for callback in self._callbacks:
                    # funcname = callback.__name__
                    action.changed.connect(_def(obj, callback))

        return action

    def _get_define_callback(
        self,
        obj: Any,
    ) -> Callable[[MagicTemplate, Any], Callable[[Any], None]]:
        from magicclass._gui import MagicTemplate

        if isinstance(obj, MagicTemplate):
            _def = define_callback_gui
        else:
            _def = define_callback
        return _def

    def as_getter(self, obj: Any) -> Callable[[Any], Any]:
        """Make a function that get the value of Widget or Action."""
        return lambda w: self._guis[id(obj)].value

    def as_remote_getter(self, obj: MagicTemplate):
        """Called when a MagicField is used in "bind"."""
        qualname = self._parent_class.__qualname__
        _LOCALS = "<locals>."
        if _LOCALS in qualname:
            qualname = qualname.split(_LOCALS)[-1]
        clsnames = qualname.split(".")

        def _func(w):
            # First we have to know where (which instance) MagicField came from.
            objname = obj.__class__.__qualname__.split(".")[-1]
            if objname not in clsnames:
                ns = ".".join(clsnames)
                raise ValueError(
                    f"{objname!r} not in {clsnames!r}. "
                    f"Method {self.name!r} is in namespace {ns!r}, so it is invisible "
                    f"from magicclass {obj.__class__.__qualname__!r}."
                )
            i = clsnames.index(objname) + 1
            # class A:
            #   class B:
            #     f = field(...)
            #   def func(self, a: Bound[B.f]): ...
            ins = obj
            for clsname in clsnames[i:]:
                ins = getattr(ins, clsname, ins)

            # Now, ins is an instance of parent class. Extract correct widget from
            # MagicField
            _field_widget = self.get_widget(ins)
            if not hasattr(_field_widget, "value"):
                raise TypeError(
                    f"MagicField {self.name} does not return ValueWidget "
                    "thus cannot be used as a bound value."
                )
            return self.as_getter(ins)(w)

        return _func

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> MagicField[_W]:
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
        """Return true if field is ready to create widgets."""
        return not self.not_ready()

    def not_ready(self) -> bool:
        return (
            self.value is Undefined
            and self.annotation is None
            and self.widget_type is None
            and "choices" not in self.options
        )

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
        return self.get_widget(self.default_object)

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
        return self.get_action(self.default_object)

    def connect(self, func: _F) -> _F:
        """Set callback function to "ready to connect" state."""
        if not callable(func):
            raise TypeError("Cannot connect non-callable object")
        elif inspect.isgeneratorfunction(func):
            warnings.warn(
                "Generator function is connected, which will not complete "
                "as a callback.",
                UserWarning,
            )
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

    @overload
    def connect_async(
        self,
        func: Callable[_P, Any | None],
        *,
        timeout: float = 0.0,
        abort_limit: float = float("inf"),
        ignore_errors: bool = False,
    ) -> thread_worker[_P]:
        ...

    @overload
    def connect_async(
        self,
        func: Literal[None],
        *,
        timeout: float = 0.0,
        abort_limit: float = float("inf"),
        ignore_errors: bool = False,
    ) -> Callable[[Callable[_P, Any | None]], thread_worker[_P]]:
        ...

    def connect_async(
        self,
        func=None,
        *,
        timeout=0.0,
        abort_limit=float("inf"),
        ignore_errors=False,
    ):
        """
        Connect a callback function to be called asynchronously.

        This method can be used similarly as ``connect`` but returns
        a ``thread_worder`` object.

        >>> @magicclass
        >>> class A:
        ...     x = field(int)
        ...     @x.connect_async
        ...     def _x_changed(self, v):
        ...         time.sleep(1)
        ...         return v
        ...     @_x_changed.returned.connect
        ...     def _x_returned(self, v):
        ...         print(v)

        Parameters
        ----------
        func : callable
            The callback function
        timeout : float, default 0.0
            Timeout second. All the callback called within this time will be
            aborted. In other words, callback will only be called every
            ``timeout`` seconds.
        abort_limit : float, default inf
            If the callback is aborted more than ``abort_limit`` seconds, it
            will not be aborted even after `timeout` seconds for the next call.
        ignore_errors : bool, default False
            If true, error will be ignored so that it does not disturb users.
        """
        from magicclass.utils import thread_worker

        def _wrapper(fn):
            if isinstance(fn, thread_worker):
                # this case is needed when multiple @connect_async are used
                # for the same function.
                return self.connect(fn)

            conn = AsyncConnection(timeout, abort_limit)

            @wraps(fn)
            def _func(self: MagicTemplate, *args, **kwargs):
                with conn.lock:
                    now = default_timer()
                    f = _afunc.__get__(self)
                    aborted_many_times = conn.is_aborted_many_times(now)
                    if conn.is_timeout(now) and not aborted_many_times:
                        if conn.abort_begin < 0:
                            conn.abort_begin = now
                        conn.quit_worker()
                        conn.running_worker = f._worker()
                    elif aborted_many_times:
                        conn.abort_begin = -1

                    conn.last_run = default_timer()
                    _last_run_copy = conn.last_run
                # call the original function
                try:
                    with self.macro.blocked():
                        out = fn(self, *args, **kwargs)
                        if isinstance(out, GeneratorType):
                            while True:
                                try:
                                    next_value = next(out)
                                except StopIteration as exc:
                                    out = exc.value
                                    break
                                if now < conn.last_completed_id:
                                    # if later function call finished earlier, current call
                                    # should never be run.
                                    return thread_worker.callback()
                                if (
                                    _last_run_copy < conn.last_run
                                    and not aborted_many_times
                                ):
                                    # if j-th call turned out to be out of date,
                                    # don't run anymore.
                                    if conn.abort_begin < 0:
                                        conn.abort_begin = now
                                    return thread_worker.callback()
                                else:
                                    yield next_value
                    if now < conn.last_completed_id:
                        return thread_worker.callback()
                    if _last_run_copy < conn.last_run and not aborted_many_times:
                        # if j-th call turned out to be out of date,
                        # don't run anymore.
                        if conn.abort_begin < 0:
                            conn.abort_begin = now
                        return thread_worker.callback()
                except Exception as exc:
                    conn.quit_worker()
                    raise exc
                if not aborted_many_times:
                    if now < conn.last_completed_id:
                        # if j-th call finished after i-th call (i < j),
                        # don't run returned callback.
                        return thread_worker.callback()
                with conn.lock:
                    conn.last_completed_id = now
                    # conn.abort_begin = -1
                yield thread_worker.callback()  # empty callback
                return out

            _afunc = thread_worker(
                _func,
                force_async=True,
                ignore_errors=ignore_errors,
            )
            _afunc.filter_errors(Aborted)
            return self.connect(_afunc)

        return _wrapper if func is None else _wrapper(func)

    # fmt: off
    @overload
    def wraps(self, method: _F, *, template: Callable | None = None, copy: bool = False) -> _F: ...
    @overload
    def wraps(self, method: None = ..., *, template: Callable | None = None, copy: bool = False) -> Callable[[_F], _F]: ...
    # fmt: on

    def wraps(self, method, *, template=None, copy=False):
        """
        Call the ``wraps`` class method of magic class.

        This method is needed when a child magic class is defined outside the main magic
        class, and integrated into the main magic class by ``field`` function, like below

        >>> @magicclass
        >>> class B:
        ...     def func(self): ...  # pre-definition

        >>> @magicclass
        >>> class A:
        ...     b = field(B)
        ...     @b.wraps
        ...     def func(self):
        ...         # do something

        Parameters
        ----------
        method : Callable, optional
            Method of parent class.
        template : Callable, optional
            Function template for signature.
        copy: bool, default False
            If true, wrapped method is still enabled.

        Returns
        -------
        Callable
            Same method as input, but has updated signature.
        """
        from magicclass._gui import BaseGui

        cls = self.constructor
        if not (isinstance(cls, type) and issubclass(cls, BaseGui)):
            raise TypeError(
                "The wraps method cannot be used for any objects but magic class."
            )
        return cls.wraps(method=method, template=template, copy=copy)

    @property
    def tooltip(self) -> str:
        """Get tooltip of returned widgets."""
        return self.options.get("tooltip", "")

    @tooltip.setter
    def tooltip(self, value):
        self.options.update(tooltip=value)

    @property
    def enabled(self) -> bool:
        """Get interactivity of returned widgets."""
        return self.options.get("enabled", True)

    @enabled.setter
    def enabled(self, value: bool):
        self.options.update(enabled=value)

    @property
    def visible(self) -> bool:
        """Get visibility of returned widgets."""
        return self.options.get("visible", True)

    @visible.setter
    def visible(self, value: bool):
        self.options.update(visible=value)

    @property
    def widget_type(self) -> type[Widget]:
        """Return type of the resulting widget."""
        return self._widget_type


class MagicValueField(MagicField[ValueWidget[_V]]):
    """
    Field class for magicgui construction. Unlike MagicField, object of this class
    always returns value itself.
    """

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> MagicValueField[_V] | _V:
        ...

    @overload
    def __get__(self, obj: Any, objtype=None) -> _V:
        ...

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self._postgethook(obj, self.get_widget(obj).value)

    def __set__(self, obj: MagicTemplate, value: _V) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        self.get_widget(obj).value = self._presethook(obj, value)

    def copy(self) -> MagicValueField[_V]:
        return super().copy()

    def post_get_hook(self, hook: Callable[[Any, _V], Any] | Callable[[_V], Any]):
        """
        Define a post-get hook for the field.

        If a post-get hook is set, value will always be converted before returned.
        Following example shows how to convert ``x`` to a float every time it gets
        accessed.

        >>> class A:
        >>>     x = vfield(int)
        >>>     @x.post_get_hook
        >>>     def _x_get(self, value):
        >>>         return float(int)

        Parameters
        ----------
        hook : callable
            Post-get hook function.
        """
        if not callable(hook):
            raise TypeError("Post-get hook must be callable.")
        if is_instance_method(hook):
            self._postgethook = hook
        else:
            self._postgethook = lambda _, x: hook(x)
        return hook

    def pre_set_hook(self, hook: Callable[[Any, Any], _V] | Callable[[Any], _V]):
        """
        Define a pre-set hook for the field.

        If a pre-set hook is set, value will always be converted before being set
        to the widget value. Following example shows how to convert ``x`` to a
        string before setting the value

        >>> class A:
        >>>     x = vfield(str)
        >>>     @x.pre_set_hook
        >>>     def _x_set(self, value):
        >>>         return str(value)

        Parameters
        ----------
        hook : callable
            Pre-set hook function.
        """
        if not callable(hook):
            raise TypeError("Pre-set hook must be callable.")
        if is_instance_method(hook):
            self._presethook = hook
        else:
            self._presethook = lambda _, x: hook(x)
        return hook

    def _postgethook(self, obj, value: _V) -> _V:
        return value

    def _presethook(self, obj, value: _V) -> _V:
        return value

    @overload
    def with_choices(self, choices: Sequence[tuple[str, _U]]) -> MagicValueField[_U]:
        ...

    @overload
    def with_choices(self, choices: Sequence[_U]) -> MagicValueField[_U]:
        ...

    @overload
    def with_choices(
        self, choices: Callable[..., Sequence[tuple[str, _U]]]
    ) -> MagicValueField[_U]:
        ...

    @overload
    def with_choices(self, choices: Callable[..., Sequence[_U]]) -> MagicValueField[_U]:
        ...

    def with_choices(self, choices):
        """Method to add choices to the field."""
        return super().with_choices(choices)


@overload
def field(
    gui_class: type[_M],
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicField[_M]:
    ...


@overload
def field(
    obj: type[_W],
    *,
    name: str | None = None,
    label: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicField[_W]:
    ...


@overload
def field(
    obj: type[_X],
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicField[ValueWidget[_X]]:
    ...


@overload
def field(
    obj: _X,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicField[ValueWidget[_X]]:
    ...


@overload
def field(
    obj: Any | None = None,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: type[_W] = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicField[_W]:
    ...


@overload
def field(
    obj: Any,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicField[Widget]:
    ...


@overload
def field(
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicField[Widget]:
    ...


def field(
    obj=Undefined,
    *,
    name=None,
    label=None,
    widget_type=None,
    options={},
    record=True,
    location=None,
):
    """
    Make a MagicField object.

    >>> i = field(1)
    >>> i = field(widget_type="Slider")

    Parameters
    ----------
    obj : Any, default Undefined
        Reference to determine what type of widget will be created. If Widget
        subclass is given, it will be used as is. If other type of class is given,
        it will used as type annotation. If an object (not type) is given, it will
        be assumed to be the default value.
    name : str, optional
        Name of the widget.
    label : str, optional
        Label of the widget.
    widget_type : str, optional
        Widget type. This argument will be sent to ``create_widget`` function.
    options : dict, optional
        Widget options. This parameter will be passed to the ``options`` keyword
        argument of ``create_widget``.
    record : bool, default True
        A magic-class specific parameter. If true, record value changes as macro.
    location : magic-class, optional
        Location to put the widget.

    Returns
    -------
    MagicField
    """
    fld = _get_field(obj, name, label, widget_type, options, record, MagicField)
    if location is not None:
        fld.set_destination(location)
    return fld


@overload
def vfield(
    widget_type: type[ValueWidget[_V]],
    *,
    name: str | None = None,
    label: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicValueField[_V]:
    ...


@overload
def vfield(
    widget_type: type[Widget],
    *,
    name: str | None = None,
    label: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicValueField[Any]:
    ...


@overload
def vfield(
    obj: type[_X],
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicValueField[_X]:
    ...


@overload
def vfield(
    obj: _X,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicValueField[_X]:
    ...


@overload
def vfield(
    obj: Any | None = None,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: type[ValueWidget[_V]] = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicValueField[_V]:
    ...


@overload
def vfield(
    obj: Any,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicValueField[Any]:
    ...


@overload
def vfield(
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
    location: type[MagicTemplate] | MagicField | None = None,
) -> MagicValueField[Any]:
    ...


def vfield(
    obj=Undefined,
    *,
    name=None,
    label=None,
    widget_type=None,
    options={},
    record=True,
    location=None,
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
    obj : Any, default Undefined
        Reference to determine what type of widget will be created. If Widget
        subclass is given, it will be used as is. If other type of class is given,
        it will used as type annotation. If an object (not type) is given, it will
        be assumed to be the default value.
    name : str, optional
        Name of the widget.
    label : str, optional
        Label of the widget.
    widget_type : str, optional
        Widget type. This argument will be sent to ``create_widget`` function.
    options : dict, optional
        Widget options. This parameter will be passed to the ``options`` keyword
        argument of ``create_widget``.
    record : bool, default True
        A magic-class specific parameter. If true, record value changes as macro.

    Returns
    -------
    MagicValueField
    """
    fld = _get_field(obj, name, label, widget_type, options, record, MagicValueField)
    if location is not None:
        fld.set_destination(location)
    return fld


def widget_property(func: Callable[..., _W]) -> MagicValueField[_W, Any]:
    """
    Create a widget property from a function.

    Generally, this decorator will be used in line with ``HasFields`` trait.
    If a widget has to be initialized depending on the state of the instance,
    you can define a field using a method.

    >>> class A(HasFields):
    >>>     def __init__(self, max: int = 10):
    >>>         self._max = max
    >>>     @widget_property
    >>>     def param(self):
    >>>         return SpinBox(value=1, max=self._max)

    In this example, ``param`` is a field object similar to those defined using
    ``vfield`` but has a variable argument ``max``.

    >>> a = A(max=20)
    >>> a.param  # Out: 1
    >>> a.param = 4  # OK
    >>> a.widgets.param  # SpinBox with value=1 and max=20

    Parameters
    ----------
    func : callable
        Widget constructor function.

    Returns
    -------
    MagicValueField
        A field with given constructor.
    """
    return MagicValueField.from_callable(func)


def _get_field(
    obj,
    name: str,
    label: str,
    widget_type: str | None,
    options: dict[str, Any],
    record: bool,
    field_class: type[MagicField],
) -> MagicField:
    if not isinstance(options, dict):
        raise TypeError(f"Field options must be a dict, got {type(options)}")
    options = options.copy()
    kwargs = dict(
        name=name, label=label, record=record, annotation=None, options=options
    )
    if is_type_like(obj):
        if is_annotated(obj):
            tp, widget_option = split_annotated_type(obj)
            kwargs.update(annotation=tp)
            options.update(**widget_option)
        if _is_magicclass(obj):
            if widget_type is not None:
                raise ValueError("Cannot specify Widget type twice.")
            f = field_class(constructor=obj, widget_type=obj, **kwargs)
        else:
            if kwargs["annotation"] is None:
                kwargs.update(annotation=obj)
            f = field_class(widget_type=widget_type, **kwargs)
    elif obj is Undefined:
        f = field_class(widget_type=widget_type, **kwargs)
    else:
        f = field_class(value=obj, widget_type=widget_type, **kwargs)

    return f


def _is_magicclass(obj: Any):
    from magicclass._gui import BaseGui

    try:
        return issubclass(obj, (Widget, BaseGui))
    except Exception:
        return False


class AsyncConnection:
    def __init__(self, timeout: float, abort_limit: float, ignore_errors: bool = False):
        self.running_worker: WorkerBase | None = None  # the running worker
        self.last_run = -1.0  # last time the worker was started
        self.last_completed_id = 0.0  # last starting time (= worker ID) that ended
        self.abort_begin = -1.0  # last time the worker started being aborted
        self._timeout = timeout
        self._abort_limit = abort_limit
        self._ignore_errors = ignore_errors
        self._lock = threading.Lock()

    def is_timeout(self, now: float) -> bool:
        return self._timeout >= now - self.last_run

    def is_aborted_many_times(self, now: float) -> bool:
        return self.abort_begin > 0 and now - self.abort_begin > self._abort_limit

    @property
    def lock(self):
        return self._lock

    def quit_worker(self):
        if self.running_worker is not None:
            self.running_worker.quit()
            self.running_worker = None

    @property
    def abort_requested(self) -> bool:
        return self.running_worker is not None and self.running_worker.abort_requested
