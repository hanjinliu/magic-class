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

from magicgui.widgets.bases import Widget, ValueWidget, ContainerWidget
from magicclass.fields import MagicField, MagicValueField, field
from magicclass.fields._define import define_callback, define_callback_gui

if TYPE_CHECKING:
    from magicclass._gui import MagicTemplate
    from magicclass.widgets._box import Box, SingleWidgetBox

_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V")


def make_constructor(
    fld: MagicField[_W],
    box_cls: type[SingleWidgetBox],
) -> Callable[[Any], SingleWidgetBox[_W]]:
    def construct_widget(obj: Any) -> Widget:
        widget = fld.construct(obj)
        return box_cls.from_widget(widget)

    return construct_widget


class BoxMagicField(MagicField["Box[_W]"], Generic[_W]):
    @classmethod
    def from_field(
        cls, fld: MagicField[_W], box_cls: type[SingleWidgetBox]
    ) -> BoxMagicField[_W]:
        """Create a field object from another field."""
        constructor = make_constructor(fld, box_cls)
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
        box_cls: type[Box],
    ) -> BoxMagicField[_W]:
        """Create a field object from a widget type."""
        fld = field(widget_type)
        return cls.from_field(fld, box_cls)

    @classmethod
    def from_any(cls, obj: Any, box_cls: type[Box]) -> BoxMagicField[_W]:
        """Create a field object from any types."""
        if isinstance(obj, MagicField):
            return cls.from_field(obj, box_cls)
        elif isinstance(obj, type):
            return cls.from_widget_type(obj, box_cls)
        else:
            raise TypeError(f"Cannot make BoxMagicField from {obj!r}")

    def get_widget(self, obj: Any) -> Box[_W]:
        from magicclass._gui import MagicTemplate

        obj_id = id(obj)
        if (widget := self._guis.get(obj_id, None)) is None:
            self._guis[obj_id] = widget = self.construct(obj)
            widget.name = self.name
            for inner in widget:
                if isinstance(inner, (ValueWidget, ContainerWidget)):
                    if isinstance(obj, MagicTemplate):
                        _def = define_callback_gui
                    else:
                        _def = define_callback
                    for callback in self._callbacks:
                        # funcname = callback.__name__
                        inner.changed.connect(_def(obj, callback))
        return widget

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

    if isinstance(obj, MagicValueField):
        return BoxMagicValueField.from_field(obj, ResizableBox)
    return BoxMagicField.from_any(obj, ResizableBox)


@_boxifier
def draggable(obj):
    """Convert a widget or a field to a draggable one."""
    from magicclass.widgets._box import DraggableBox

    if isinstance(obj, MagicValueField):
        return BoxMagicValueField.from_field(obj, DraggableBox)
    return BoxMagicField.from_any(obj, DraggableBox)


@_boxifier
def scrollable(obj):
    """Convert a widget or a field to a scrollable one."""
    from magicclass.widgets._box import ScrollableBox

    if isinstance(obj, MagicValueField):
        return BoxMagicValueField.from_field(obj, ScrollableBox)
    return BoxMagicField.from_any(obj, ScrollableBox)


@_boxifier
def collapsible(obj, orientation: Literal["horizontal", "vertical"] = "vertical"):
    """Convert a widget or a field to a collapsible one."""
    from magicclass.widgets._box import CollapsibleBox, HCollapsibleBox

    if orientation == "vertical":
        box_cls = CollapsibleBox
    elif orientation == "horizontal":
        box_cls = HCollapsibleBox
    else:
        raise ValueError(f"Invalid orientation: {orientation!r}")

    if isinstance(obj, MagicValueField):
        return BoxMagicValueField.from_field(obj, box_cls)
    return BoxMagicField.from_any(obj, box_cls)
