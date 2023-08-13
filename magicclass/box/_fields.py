from __future__ import annotations
from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
    Generic,
    Literal,
    Protocol,
    TypeVar,
    overload,
)
from typing_extensions import Concatenate, ParamSpec
from magicgui.widgets.bases import Widget, ValueWidget, ContainerWidget
from magicclass.fields import MagicField, MagicValueField, field
from magicclass.fields._define import define_callback, define_callback_gui

if TYPE_CHECKING:
    from magicclass._gui import MagicTemplate
    from magicclass.widgets._box import SingleWidgetBox

_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V")
_F = TypeVar("_F", bound=Callable)
_P = ParamSpec("_P")


class _FieldConstructor(Generic[_W]):
    def __init__(
        self,
        fld: MagicField[_W],
        box_cls: type[SingleWidgetBox],
        **kwargs,
    ):
        self._field = fld
        self._box_cls = box_cls
        self._box_cls_kwargs = kwargs

    @property
    def field(self) -> MagicField[_W]:
        return self._field

    def __call__(self, obj: Any) -> SingleWidgetBox[_W]:
        widget = self._field.construct(obj)
        return self._box_cls.from_widget(widget, **self._box_cls_kwargs)


class BoxMagicField(MagicField["SingleWidgetBox[_W]"], Generic[_W]):
    @classmethod
    def from_field(
        cls,
        fld: MagicField[_W],
        box_cls: type[SingleWidgetBox],
        **kwargs,
    ) -> BoxMagicField[_W]:
        """Create a field object from another field."""
        constructor = _FieldConstructor(fld, box_cls, **kwargs)
        return cls(
            value=fld.value,
            name=fld.name,
            label=fld.label,
            annotation=fld.annotation,
            widget_type=box_cls,
            options=fld.options,
            record=fld.record,
            constructor=constructor,
        )

    @classmethod
    def from_widget_type(
        cls,
        widget_type: type[_W],
        box_cls: type[SingleWidgetBox],
        **kwargs,
    ) -> BoxMagicField[_W]:
        """Create a field object from a widget type."""
        fld = field(widget_type)
        return cls.from_field(fld, box_cls, **kwargs)

    @classmethod
    def from_any(
        cls,
        obj: Any,
        box_cls: type[SingleWidgetBox],
        **kwargs,
    ) -> BoxMagicField[_W]:
        """Create a field object from any types."""
        if isinstance(obj, MagicField):
            return cls.from_field(obj, box_cls, **kwargs)
        elif isinstance(obj, type):
            return cls.from_widget_type(obj, box_cls, **kwargs)
        else:
            raise TypeError(f"Cannot make BoxMagicField from {obj!r}")

    def get_widget(self, obj: Any) -> SingleWidgetBox[_W]:
        from magicclass._gui import MagicTemplate

        obj_id = id(obj)
        if (box := self._guis.get(obj_id, None)) is None:
            self._guis[obj_id] = box = self.construct(obj)
            box.name = self.name
            inner = box.widget
            if isinstance(inner, (ValueWidget, ContainerWidget)):
                if isinstance(obj, MagicTemplate):
                    _def = define_callback_gui
                else:
                    _def = define_callback
                for callback in self._callbacks:
                    # funcname = callback.__name__
                    inner.changed.connect(_def(obj, callback))
        return box

    def as_getter(self, obj: Any) -> Callable[[Any], Any]:
        """Make a function that get the value of Widget or Action."""
        return lambda w: self._guis[id(obj)].widget.value

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> BoxMagicField[_W]:
        ...

    @overload
    def __get__(self, obj: Any, objtype=None) -> _W:
        ...

    def __get__(self, obj, objtype=None):
        """Get widget for the object."""
        if obj is None:
            return self
        return _unbox(self.get_widget(obj))

    # fmt: off
    @overload
    def wraps(self, method: _F, *, template: Callable | None = None, copy: bool = False) -> _F: ...
    @overload
    def wraps(self, method: None = ..., *, template: Callable | None = None, copy: bool = False) -> Callable[[_F], _F]: ...
    # fmt: on

    def wraps(self, method, *, template=None, copy=False):
        """
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
        from magicclass._gui import BaseGui

        cst = self.constructor
        if isinstance(cst, _FieldConstructor):
            return cst.field.wraps(method=method, template=template, copy=copy)
        elif not (isinstance(cst, type) and issubclass(cst, BaseGui)):
            raise TypeError(
                "The wraps method cannot be used for any objects but magic class."
            )
        return cst.wraps(method=method, template=template, copy=copy)


class BoxMagicValueField(BoxMagicField[ValueWidget[_V]]):
    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> BoxMagicValueField[_V]:
        ...

    @overload
    def __get__(self, obj: Any, objtype=None) -> _V:
        ...

    def __get__(self, obj, objtype=None):
        """Get widget for the object."""
        if obj is None:
            return self
        return _unbox(self.get_widget(obj)).value

    def __set__(self, obj: MagicTemplate, value: _V) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        _unbox(self.get_widget(obj)).value = value


def _unbox(w: SingleWidgetBox[_W]) -> _W:
    from magicclass.widgets._box import SingleWidgetBox

    while isinstance(w, SingleWidgetBox):
        w = w.widget
    return w


class BoxProtocol(Protocol[_P]):
    @overload
    def __call__(
        self, fld: BoxMagicValueField[_V], *args: _P.args, **kwargs: _P.kwargs
    ) -> BoxMagicValueField[_V]:
        ...

    @overload
    def __call__(
        self, fld: BoxMagicField[_W], *args: _P.args, **kwargs: _P.kwargs
    ) -> BoxMagicField[_W]:
        ...

    @overload
    def __call__(
        self, fld: MagicValueField[_V], *args: _P.args, **kwargs: _P.kwargs
    ) -> BoxMagicValueField[_V]:
        ...

    @overload
    def __call__(
        self, fld: MagicField[_W], *args: _P.args, **kwargs: _P.kwargs
    ) -> BoxMagicField[_W]:
        ...

    @overload
    def __call__(
        self, widget_type: type[_W], *args: _P.args, **kwargs: _P.kwargs
    ) -> BoxMagicField[_W]:
        ...


# fmt: off
if TYPE_CHECKING:
    def _boxifier(f: Callable[Concatenate[Any, _P], Any]) -> BoxProtocol[_P]: ...
else:
    _boxifier = lambda x: x
# fmt: on


@_boxifier
def resizable(
    obj,
    x_enabled: bool = True,
    y_enabled: bool = True,
):
    """Convert a widget or a field to a resizable one."""
    from magicclass.widgets._box import ResizableBox

    kwargs = {"x_enabled": x_enabled, "y_enabled": y_enabled}
    if isinstance(obj, (MagicValueField, BoxMagicValueField)):
        return BoxMagicValueField.from_field(obj, ResizableBox, **kwargs)
    else:
        return BoxMagicField.from_any(obj, ResizableBox, **kwargs)


@_boxifier
def draggable(obj):
    """Convert a widget or a field to a draggable one."""
    from magicclass.widgets._box import DraggableBox

    if isinstance(obj, (MagicValueField, BoxMagicValueField)):
        return BoxMagicValueField.from_field(obj, DraggableBox)
    return BoxMagicField.from_any(obj, DraggableBox)


@_boxifier
def scrollable(
    obj,
    x_enabled: bool = True,
    y_enabled: bool = True,
):
    """Convert a widget or a field to a scrollable one."""
    from magicclass.widgets._box import ScrollableBox

    kwargs = {"x_enabled": x_enabled, "y_enabled": y_enabled}
    if isinstance(obj, (MagicValueField, BoxMagicValueField)):
        return BoxMagicValueField.from_field(obj, ScrollableBox, **kwargs)
    else:
        return BoxMagicField.from_any(obj, ScrollableBox, **kwargs)


@_boxifier
def collapsible(
    obj,
    orientation: Literal["horizontal", "vertical"] = "vertical",
    text: str | None = None,
):
    """Convert a widget or a field to a collapsible one."""
    from magicclass.widgets._box import CollapsibleBox, HCollapsibleBox

    if orientation == "vertical":
        box_cls = CollapsibleBox
    elif orientation == "horizontal":
        box_cls = HCollapsibleBox
    else:
        raise ValueError(f"Invalid orientation: {orientation!r}")
    kwargs = {"text": text} if text is not None else {}
    if isinstance(obj, (MagicValueField, BoxMagicValueField)):
        return BoxMagicValueField.from_field(obj, box_cls, **kwargs)
    else:
        return BoxMagicField.from_any(obj, box_cls, **kwargs)
