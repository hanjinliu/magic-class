from __future__ import annotations
from typing import Any, Iterable, TypeVar, overload, Iterator, Tuple, Sequence
from typing_extensions import get_args, get_origin, _AnnotatedAlias
import inspect
from magicgui.types import WidgetOptions
from magicgui.signature import split_annotated_type
from magicgui.widgets import create_widget, Container, PushButton, EmptyWidget
from magicgui.widgets._bases.value_widget import UNSET, ValueWidget, _Unset
from magicgui.widgets._concrete import merge_super_sigs

_V = TypeVar("_V")


@merge_super_sigs
class ListEdit(Container):
    """A widget to represent a list of values.
    A ListEdit container can create a list with multiple objects of same type. It
    will contain many child widgets and their value is represented as a Python list
    object. If a list is given as the initial value, types of child widgets are
    determined from the contents. Number of contents can be adjusted with +/-
    buttons.
    Parameters
    ----------
    options: WidgetOptions, optional
        Widget options of child widgets.
    """

    def __init__(
        self,
        value: Iterable[_V] | _Unset = UNSET,
        layout: str = "horizontal",
        labels: bool = False,
        nullable: bool = False,
        options: WidgetOptions = None,
        **kwargs,
    ):
        self._args_type: type | None = None
        self._nullable = nullable
        self._child_options = options or {}

        super().__init__(layout=layout, labels=labels, **kwargs)
        self.margins = (0, 0, 0, 0)

        if not isinstance(value, _Unset):
            types = {type(a) for a in value}
            if len(types) == 1:
                if self._args_type is None:
                    self._args_type = types.pop()
            else:
                raise TypeError("values have inconsistent types.")
            _value: Iterable[_V] = value
        else:
            _value = []

        button_plus = PushButton(text="+", name="plus")
        button_plus.changed.connect(lambda: self._append_value())

        button_minus = PushButton(text="-", name="minus")
        button_minus.changed.connect(self._pop_value)

        if layout == "horizontal":
            button_plus.max_width = 40
            button_minus.max_width = 40

        self.append(button_plus)
        self.append(button_minus)

        for a in _value:
            self._append_value(a)

        self.btn_plus = button_plus
        self.btn_minus = button_minus

    @property
    def annotation(self):
        """Return type annotation for the parameter represented by the widget.
        ForwardRefs will be resolve when setting the annotation. For ListEdit,
        annotation will be like 'list[str]'.
        """
        return self._annotation

    @annotation.setter
    def annotation(self, value):
        if value is None:
            self._annotation = None
            self._args_type = None
            return

        from magicgui._type_wrapper import resolve_annotation

        value = resolve_annotation(value)
        arg: type | None = None

        if value and value is not inspect.Parameter.empty:
            from magicgui.type_map import _is_subclass

            orig = get_origin(value)
            if not (_is_subclass(orig, list) or isinstance(orig, list)):
                raise TypeError(
                    f"cannot set annotation {value} to {type(self).__name__}."
                )
            args = get_args(value)
            if len(args) > 0:
                arg = args[0]
            else:
                arg = None

        if isinstance(arg, _AnnotatedAlias):
            arg, metadata = split_annotated_type(arg)
            if self._child_options and metadata:
                raise ValueError(
                    "Cannot set options from 'options' argument and Annotated type."
                )
            self._child_options = metadata

        self._annotation = value
        self._args_type = arg

    def _append_value(self, value=UNSET):
        """Create a new child value widget and append it."""
        i = len(self) - 2

        widget = create_widget(
            annotation=self._args_type,
            name=f"value_{i}",
            label=f"({i})",
            options=self._child_options,
        )

        if isinstance(widget, EmptyWidget):
            raise TypeError("could not determine the type of child widget.")

        self.insert(i, widget)

        # Value must be set after new widget is inserted because it could be
        # valid only after same parent is shared between widgets.
        if value is UNSET and i > 0:
            value = self[i - 1].value  # type: ignore
        if value is not UNSET:
            widget.value = value

    def _pop_value(self):
        """Delete last child value widget."""
        try:
            self.pop(-3)
        except IndexError:
            pass

    @property
    def buttons_visible(self) -> bool:
        """Toggle visibility of +/- buttons."""
        return self.btn_plus.visible

    @buttons_visible.setter
    def buttons_visible(self, v: bool) -> None:
        self.btn_plus.visible = v
        self.btn_minus.visible = v

    @property
    def value(self) -> list:
        """Return current value as a list object."""
        return list(ListDataView(self))

    @value.setter
    def value(self, vals: Iterable[_V]):
        del self[:-2]
        for v in vals:
            self._append_value(v)

    @property
    def data(self) -> ListDataView:
        """Return a data view of current value."""
        return ListDataView(self)

    @data.setter
    def data(self, vals: Iterable[_V]):
        del self[:-2]
        for v in vals:
            self._append_value(v)


class ListDataView:
    """Data view of ListEdit."""

    def __init__(self, obj: ListEdit):
        self._obj = obj
        self._widgets: list[ValueWidget] = list(obj[:-2])  # type: ignore

    def __repr__(self):
        """A list-like representation."""
        return f"{self.__class__.__name__}({list(self)!r})"

    def __len__(self):
        """Length as a list."""
        return len(self._widgets)

    def __eq__(self, other):
        """Compare as a list."""
        return list(self) == other

    @overload
    def __getitem__(self, i: int) -> _V:  # noqa
        ...

    @overload
    def __getitem__(self, key: slice) -> list[_V]:  # noqa
        ...

    def __getitem__(self, key):
        """Slice as a list."""
        if isinstance(key, int):
            return self._widgets[key].value
        elif isinstance(key, slice):
            return [w.value for w in self._widgets[key]]
        else:
            raise TypeError(
                f"list indices must be integers or slices, not {type(key).__name__}"
            )

    @overload
    def __setitem__(self, key: int, value: _V) -> None:  # noqa
        ...

    @overload
    def __setitem__(self, key: slice, value: _V | Iterable[_V]) -> None:  # noqa
        ...

    def __setitem__(self, key, value):
        """Update widget value."""
        if isinstance(key, int):
            self._widgets[key].value = value
        elif isinstance(key, slice):
            if isinstance(value, type(self._widgets[0].value)):
                for w in self._widgets[key]:
                    w.value = value
            else:
                for w, v in zip(self._widgets[key], value):
                    w.value = v
        else:
            raise TypeError(
                f"list indices must be integers or slices, not {type(key).__name__}"
            )

    @overload
    def __delitem__(self, key: int) -> None:  # noqa
        ...

    @overload
    def __delitem__(self, key: slice) -> None:  # noqa
        ...

    def __delitem__(self, key):
        """Delete widget at the key(s)."""
        self._obj.__delitem__(key)

    def __iter__(self) -> Iterator[_V]:
        """Iterate over values of child widgets."""
        for w in self._widgets:
            yield w.value


@merge_super_sigs
class TupleEdit(Container):
    """A widget to represent a tuple of values.
    A TupleEdit container has several child widgets of different type. Their value is
    represented as a Python tuple object. If a tuple is given as the initial value,
    types of child widgets are determined one by one. Unlike ListEdit, number of
    contents is not editable.
    Parameters
    ----------
    options: WidgetOptions, optional
        Widget options of child widgets.
    """

    def __init__(
        self,
        value: Iterable[_V] | _Unset = UNSET,
        layout: str = "horizontal",
        nullable: bool = False,
        options: WidgetOptions = None,
        **kwargs,
    ):
        self._nullable = nullable
        self._args_types: tuple[type, ...] | None = None
        super().__init__(layout=layout, labels=False, **kwargs)
        self._child_options = options or {}
        self.margins = (0, 0, 0, 0)

        if not isinstance(value, _Unset):
            if self._args_types is None:
                self._args_types = tuple(type(a) for a in value)
            _value: Iterable[Any] = value
        elif self._args_types is not None:
            _value = (UNSET,) * len(self._args_types)
        else:
            raise ValueError(
                "Either 'value' or 'annotation' must be specified in "
                f"{type(self).__name__}."
            )

        for i, a in enumerate(_value):
            annot = self._args_types[i]
            if isinstance(annot, _AnnotatedAlias):
                annot, metadata = split_annotated_type(annot)
                options = self._child_options.copy()
                options.update(metadata)
            else:
                options = self._child_options
            widget = create_widget(
                value=a,
                annotation=annot,
                name=f"value_{i}",
                options=options,
            )
            self.insert(i, widget)

    def __iter__(self) -> Iterator[ValueWidget]:
        """Just for typing."""
        return super().__iter__()  # type: ignore

    @property
    def annotation(self):
        """Return type annotation for the parameter represented by the widget.
        ForwardRefs will be resolve when setting the annotation. For TupleEdit,
        annotation will be like 'tuple[str, int]'.
        """
        return self._annotation

    @annotation.setter
    def annotation(self, value):
        if value is None:
            self._annotation = None
            self._args_types = None
            return
        from magicgui._type_wrapper import resolve_annotation

        value = resolve_annotation(value)
        args: tuple[type, ...] | None = None

        if value and value is not inspect.Parameter.empty:
            from magicgui.type_map import _is_subclass

            orig = get_origin(value)
            if not (_is_subclass(orig, tuple) or isinstance(orig, tuple)):
                raise TypeError(
                    f"cannot set annotation {value} to {type(self).__name__}."
                )
            args = get_args(value)
            value = Tuple[args]

        self._annotation = value
        self._args_types = args

    @property
    def value(self) -> tuple:
        """Return current value as a tuple."""
        return tuple(w.value for w in self)

    @value.setter
    def value(self, vals: Sequence):
        if len(vals) != len(self):
            raise ValueError("Length of tuple does not match.")

        for w, v in zip(self, vals):
            w.value = v  # type: ignore
