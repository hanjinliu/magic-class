from __future__ import annotations
from typing import Any, Callable, TYPE_CHECKING, Literal, Protocol, TypeVar, overload

from magicgui.widgets.bases import Widget, ValueWidget
from magicclass.fields import MagicField, MagicValueField

if TYPE_CHECKING:
    from magicclass._gui import MagicTemplate
    from magicclass.widgets._box import Box

_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V")


def make_constructor(
    fld: MagicField[_W],
    box_cls: type[Box],
) -> Callable[[Any], Box[_W]]:
    def construct_widget(obj: Any) -> Widget:
        widget = fld.construct(obj)
        return box_cls.from_widget(widget)

    return construct_widget


class BoxMagicField(MagicField[_W]):
    @classmethod
    def from_field(cls, fld: MagicField[_W], box_cls: type[Box]) -> BoxMagicField[_W]:
        constructor = make_constructor(fld, box_cls)
        return cls(
            value=fld.value,
            name=fld.name,
            label=fld.label,
            annotation=fld.annotation,
            widget_type=box_cls,
            options=fld.options,
            constructor=constructor,
        )

    @classmethod
    def from_widget_type(
        cls,
        widget_type: type[_W],
        box_cls: type[Box],
    ) -> BoxMagicField[_W]:
        fld = MagicField(widget_type=widget_type)
        return cls.from_field(fld, box_cls)

    @classmethod
    def from_any(cls, obj: Any, box_cls: type[Box]) -> BoxMagicField[_W]:
        if isinstance(obj, MagicField):
            return cls.from_field(obj, box_cls)
        elif isinstance(obj, type):
            return cls.from_widget_type(obj, box_cls)
        else:
            raise TypeError(f"Cannot make BoxMagicField from {obj!r}")

    def get_widget(self, obj: Any) -> Box[_W]:
        return super().get_widget(obj)

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
        return self.get_widget(obj).widget


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
        return self.get_widget(obj).widget.value

    def __set__(self, obj: MagicTemplate, value: _V) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        self.get_widget(obj).widget.value = value


class BoxProtocol(Protocol):
    @overload
    def __call__(self, fld: MagicField[_W]) -> BoxMagicField[_W]:
        ...

    @overload
    def __call__(self, widget_type: type[_W]) -> BoxMagicField[_W]:
        ...

    @overload
    def __call__(self, fld: MagicValueField[_V]) -> BoxMagicValueField[_V]:
        ...


if TYPE_CHECKING:

    def _boxifier(f) -> BoxProtocol:
        ...  # fmt: skip

else:
    _boxifier = lambda x: x


@_boxifier
def resizable(obj):
    """Convert a widget or a field to a resizable one."""
    from magicclass.widgets._box import ResizableBox

    return BoxMagicField.from_any(obj, ResizableBox)


@_boxifier
def draggable(obj):
    """Convert a widget or a field to a draggable one."""
    from magicclass.widgets._box import DraggableBox

    return BoxMagicField.from_any(obj, DraggableBox)


@_boxifier
def scrollable(obj):
    """Convert a widget or a field to a scrollable one."""
    from magicclass.widgets._box import ScrollableBox

    return BoxMagicField.from_any(obj, ScrollableBox)


@_boxifier
def collapsible(obj):
    """Convert a widget or a field to a collapsible one."""
    from magicclass.widgets._box import CollapsibleBox

    return BoxMagicField.from_any(obj, CollapsibleBox)
