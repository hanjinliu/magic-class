from __future__ import annotations

from typing import Generic, TypeVar, Callable, Any
import inspect
from psygnal import debounced, Signal
from magicgui.signature import magic_signature
from magicgui.widgets import create_widget, Container, PushButton
from magicgui.widgets.bases import ValueWidget
from magicclass.signature import split_annotated_type
from ._fields import MagicField
from ._define import define_callback

_V = TypeVar("_V")


class _ButtonedWidget(Container):
    """A widget wrapper that adds a button to set the value."""

    restoring = Signal()

    def __init__(
        self,
        widget: ValueWidget,
        layout: str = "horizontal",
        call_button: str | bool | None = None,
        auto_call: bool = False,
        **kwargs,
    ):
        if not hasattr(widget, "value"):
            raise TypeError("widget must have a value attribute")
        self._child_widget = widget

        widgets = [widget]
        if call_button is None:
            call_button = not auto_call

        self._call_button: PushButton | None = None
        if call_button:
            text = call_button if isinstance(call_button, str) else "Set"
            self._call_button = PushButton(gui_only=True, text=text, name="call_button")
            widgets.append(self._call_button)

        super().__init__(layout=layout, widgets=widgets, labels=False, **kwargs)
        self.margins = (0, 0, 0, 0)
        # disconnect the existing signals
        widget.changed.disconnect()
        if self._call_button is not None:
            self._call_button.changed.disconnect()
            self._call_button.changed.connect(self._button_clicked)
        self._auto_call = auto_call
        self._inner_value = widget.value

        if auto_call:
            widget.changed.connect(self.set_value)
        else:

            @self.restoring.connect
            def _restore():
                with widget.changed.blocked():
                    self.widget.value = self._inner_value
                return None

            widget.changed.connect(self._create_debounced())

    @classmethod
    def from_options(
        cls: type[_ButtonedWidget],
        annotation: type,
        layout: str = "horizontal",
        widget_type: type | None = None,
        options: dict | None = None,
        call_button: str | bool | None = None,
        auto_call=False,
        **kwargs,
    ):
        """Construct a ButtonedWidget in a ``create_widget`` format."""
        widget = create_widget(
            annotation=annotation,
            widget_type=widget_type,
            options=options,
        )
        return cls(widget, layout, call_button, auto_call, **kwargs)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.widget!r})"

    @property
    def value(self) -> Any:
        """The value that has been set (not the widget)."""
        return self._inner_value

    @value.setter
    def value(self, value: Any) -> None:
        return self.set_value(value)

    def set_value(self, value: Any) -> None:
        """Method version of setting the value."""
        self.widget.value = value
        self._inner_value = self.widget.value
        self.changed.emit(self._inner_value)
        return None

    def _button_clicked(self):
        self._inner_value = self.widget.value
        self.changed.emit(self._inner_value)
        return None

    @property
    def widget(self) -> ValueWidget:
        """The central child widget."""
        return self._child_widget

    @property
    def call_button(self) -> PushButton | None:
        """The call button widget."""
        return self._call_button

    def _create_debounced(self):
        @debounced(timeout=1000)
        def _reset_value(val):
            if self.widget.native.hasFocus():
                _reset_value(val)
            else:
                self.restoring.emit()

        return lambda v: _reset_value(v)


class magicproperty(MagicField[_ButtonedWidget], Generic[_V]):
    """
    A property-like descriptor that returns a field for magicgui widgets.

    For instance, the following code

    >>> @magicproperty
    >>> def x(self):
    >>>     return self._x

    >>> @x.setter
    >>> def x(self, val: int):
    >>>     self._x = val

    will create a magicgui widget with a button "Set".
    """

    def __init__(
        self,
        fget: Callable[[Any], _V] | None = None,
        fset: Callable[[Any, _V], None] | None = None,
        fdel: Callable[[Any], None] | None = None,
        *,
        name: str | None = None,
        label: str | None = None,
        annotation: Any = None,
        widget_type: type | str | None = None,
        auto_call: bool = False,
        layout: str = "horizontal",
        call_button: bool | str | None = None,
        options: dict[str, Any] | None = None,
        record: bool = True,
    ) -> None:
        def _create_buttoned_gui(obj):
            return _ButtonedWidget.from_options(
                annotation=self.annotation,
                layout=layout,
                widget_type=self.widget_type,
                options=self.options,
                call_button=call_button,
                auto_call=auto_call,
                name=self.name,
            )

        super().__init__(
            name=name,
            label=label,
            annotation=annotation,
            widget_type=widget_type,
            options=options,
            record=record,
            constructor=_create_buttoned_gui,
        )

        self._fget = self._default_fget
        self._fset = self._default_fset

        if fget:
            self.getter(fget)
        if fset:
            self.setter(fset)
        if fdel:
            self.deleter(fdel)

    @classmethod
    def from_setter(
        cls: type[magicproperty],
        fset: Callable[[Any, _V], None] = None,
        *,
        name: str | None = None,
        label: str | None = None,
        annotation: Any = None,
        widget_type: type | str | None = None,
        auto_call: bool = False,
        layout: str = "horizontal",
        call_button: bool | str | None = None,
        options: dict[str, Any] | None = None,
        record: bool = True,
    ) -> magicproperty[_V]:
        """
        Directly create a magicproperty from a setter function.

        Example
        -------
        >>> @magicproperty.from_setter
        >>> def x(self, val: int):
        ...     print(f"setting x to {val}")

        >>> @magicproperty.from_setter(label="X")
        >>> def x(self, val: int):
        ...     print(f"setting x to {val}")

        """

        def _wrapper(fset):
            return cls(
                fset=fset,
                name=name,
                label=label,
                annotation=annotation,
                widget_type=widget_type,
                auto_call=auto_call,
                layout=layout,
                call_button=call_button,
                options=options,
                record=record,
            )

        return _wrapper if fset is None else _wrapper(fset)

    def copy(self) -> magicproperty[_V]:
        raise NotImplementedError

    def getter(self, fget: Callable[[Any], _V]) -> magicproperty[_V]:
        """Define a getter function."""
        self._fget = fget
        if self.label is None:
            self.label = fget.__name__.replace("_", " ")
        if return_annotation := fget.__annotations__.get("return", None):
            self.annotation = return_annotation
        return self

    __call__ = getter

    def setter(self, fset: Callable[[Any, _V], None]) -> magicproperty[_V]:
        """Define a setter function."""
        self._fset = fset
        if self.label is None:
            self.label = fset.__name__.replace("_", " ")

        _self, _val = magic_signature(fset).parameters.values()
        annot, opt = split_annotated_type(_val.annotation)
        if not self.options:
            self.options = opt
        if "widget_type" in opt:
            self.widget_type = opt.pop("widget_type")
        if self.annotation in (None, inspect.Parameter.empty):
            self.annotation = annot
        return self

    def deleter(self, fdel: Callable[[Any], None]) -> magicproperty[_V]:
        """Define a deleter function."""
        self._fdel = fdel
        return self

    def __set_name__(self, owner: type, name: str) -> None:
        super().__set_name__(owner, name)
        if not hasattr(owner, "__annotations__"):
            return None
        if annotation := owner.__annotations__.get(name):
            self.annotation = annotation

    def _default_fget(self, obj) -> _V:
        """Return the widget value by default."""
        return self.get_widget(obj).value

    def _default_fset(self, obj, val) -> None:
        """Do nothing other than updating the value."""

    def __get__(self, obj: Any, objtype: Any = None) -> _V:
        if obj is None:
            return self
        return self._fget(obj)

    def __set__(self, obj: Any, value: _V) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        # first set the value on the widget to check if it's valid
        gui = self.get_widget(obj)
        old_value = gui.value
        with gui.changed.blocked():
            gui.value = value
            try:
                self._fset(obj, value)
            except Exception:
                gui.value = old_value
                raise

        gui.changed.emit(value)

        return None

    def __delete__(self, obj: Any) -> None:
        if self._fdel is not None:
            return self._fdel(obj)
        raise AttributeError("can't delete attribute")

    def get_widget(self, obj: Any) -> _ButtonedWidget:
        """A light-weight version."""
        obj_id = id(obj)
        if (widget := self._guis.get(obj_id, None)) is None:
            self._guis[obj_id] = widget = self.construct(obj)
            widget.name = self.name
            for callback in self._callbacks:
                widget.changed.connect(define_callback(obj, callback))
            widget.changed.connect(lambda val: self._fset(obj, val))
        return widget
