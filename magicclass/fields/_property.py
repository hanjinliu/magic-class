from __future__ import annotations

from typing import TypeVar, Callable, Any, TYPE_CHECKING
from magicgui.signature import magic_signature
from magicgui.widgets import create_widget, Container, PushButton
from magicgui.widgets._bases import ValueWidget
from ._fields import MagicField
from ._define import define_callback
from ..signature import split_annotated_type

_V = TypeVar("_V")

if TYPE_CHECKING:
    from typing_extensions import Self


class _ButtonedWidget(Container):
    def __init__(
        self,
        widget: ValueWidget,
        layout: str = "horizontal",
        call_button: str | bool | None = None,
        auto_call=False,
        **kwargs,
    ):
        if not hasattr(widget, "value"):
            raise TypeError("widget must have a value attribute")
        self._child_widget = widget

        if call_button is None:
            call_button = not auto_call
        if call_button:
            self._call_button: PushButton | None = None
            text = call_button if isinstance(call_button, str) else "Set"
            self._call_button = PushButton(gui_only=True, text=text, name="call_button")

        super().__init__(
            layout=layout, widgets=[widget, self._call_button], labels=False, **kwargs
        )
        self.margins = (0, 0, 0, 0)
        # disconnect the existing signals
        widget.changed.disconnect()
        self._call_button.changed.disconnect()
        self._call_button.changed.connect(self._button_clicked)
        self._auto_call = auto_call
        self._inner_value = widget.value

        if auto_call:
            widget.changed.connect(self.set_value)

    @classmethod
    def from_anotation(
        cls: type[_ButtonedWidget],
        annotation: type,
        layout: str = "horizontal",
        widget_type: type | None = None,
        options: dict | None = None,
        call_button: str | bool | None = None,
        auto_call=False,
        **kwargs,
    ):
        widget = create_widget(
            annotation=annotation, widget_type=widget_type, options=options
        )
        return cls(widget, layout, call_button, auto_call, **kwargs)

    @property
    def value(self) -> Any:
        """The value that has been set (not the widget)."""
        return self._inner_value

    @value.setter
    def value(self, value: Any) -> None:
        return self.set_value(value)

    def set_value(self, value: Any) -> None:
        """Method version of setting the value."""
        self._child_widget.value = value
        self._inner_value = self.value
        self.changed.emit(self._inner_value)
        return None

    def _button_clicked(self):
        self._inner_value = self.widget.value
        self.changed.emit(self._inner_value)
        return None

    @property
    def widget(self) -> ValueWidget:
        return self._child_widget

    @property
    def call_button(self) -> PushButton:
        return self._call_button


class magicproperty(MagicField[_ButtonedWidget, _V]):
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
        self._fget = fget
        self._fset = fset
        self._fdel = fdel

        if call_button is None:
            call_button = "Set"

        def _create_buttoned_gui(obj):
            return _ButtonedWidget.from_anotation(
                self.annotation,
                call_button=call_button,
                layout=layout,
                auto_call=auto_call,
                options=self.options,
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

    def copy(self) -> Self[_V]:
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
        if not self.annotation:
            self.annotation = annot
        return self

    def deleter(self, fdel: Callable[[Any], None]) -> magicproperty[_V]:
        """Define a deleter function."""
        self._fdel = fdel
        return self

    def __get__(self, obj: Any, objtype: Any = None) -> _V:
        if obj is None:
            return self
        if self._fget is not None:
            return self._fget(obj)
        else:
            return self.get_widget(obj).value

    def __set__(self, obj: Any, value: _V) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        # first set the value on the widget to check if it's valid
        gui = self.get_widget(obj)
        param_widget = gui.widget
        old_value = param_widget.value
        param_widget.value = value
        try:
            self._fset(obj, value)
        except Exception:
            param_widget.value = old_value
            raise
        return None

    def __delete__(self, obj: Any) -> None:
        if self._fdel is not None:
            return self._fdel(obj)
        raise AttributeError("can't delete attribute")

    def not_ready(self) -> bool:
        return self._fset is None

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
