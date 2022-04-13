from __future__ import annotations
from typing import Any, TYPE_CHECKING, Callable, TypeVar
import re
from magicgui.widgets import PushButton
from magicgui.widgets._concrete import _LabeledWidget
from magicgui.widgets._bases import ValueWidget, ButtonWidget, ContainerWidget
from magicgui.widgets._function_gui import (
    FunctionGui,
    _function_name_pointing_to_widget,
)

from ..widgets import Separator

if TYPE_CHECKING:
    from magicgui.widgets._bases import Widget


_R = TypeVar("_R")


class FunctionGuiPlus(FunctionGui[_R]):
    """FunctionGui class with a parameter recording functionality etc."""

    _preview = None

    def __call__(self, *args: Any, update_widget: bool = False, **kwargs: Any) -> _R:
        sig = self.__signature__
        try:
            bound = sig.bind(*args, **kwargs)
        except TypeError as e:
            if "missing a required argument" in str(e):
                match = re.search("argument: '(.+)'", str(e))
                missing = match.groups()[0] if match else "<param>"
                msg = (
                    f"{e} in call to '{self._callable_name}{sig}'.\n"
                    "To avoid this error, you can bind a value or callback to the "
                    f"parameter:\n\n    {self._callable_name}.{missing}.bind(value)"
                    "\n\nOr use the 'bind' option in the set_option decorator:\n\n"
                    f"    @set_option({missing}={{'bind': value}})\n"
                    f"    def {self._callable_name}{sig}: ..."
                )
                raise TypeError(msg) from None
            else:
                raise

        if update_widget:
            self._auto_call, before = False, self._auto_call
            try:
                self.update(bound.arguments)
            finally:
                self._auto_call = before

        bound.apply_defaults()

        # 1. Parameter recording
        # This is important when bound function set by {"bind": f} updates something.
        # When the value is referred via "__signature__" the bound function get called
        # and updated againg.
        self._previous_bound = bound

        self._tqdm_depth = 0  # reset the tqdm stack count
        with _function_name_pointing_to_widget(self):
            # 2. Running flag
            # We sometimes want to know if the function is called programmatically or
            # from GUI. The "running" argument is True only when it's called via GUI.
            self.running = True
            try:
                value = self._function(*bound.args, **bound.kwargs)
            finally:
                self.running = False

        self._call_count += 1
        if self._result_widget is not None:
            with self._result_widget.changed.blocked():
                self._result_widget.value = value

        return_type = sig.return_annotation
        if return_type:
            from magicgui.type_map import _type2callback

            for callback in _type2callback(return_type):
                callback(self, value, return_type)
        self.called.emit(value)
        return value

    def insert(self, key: int, widget: Widget):
        """Insert widget at ``key``."""
        if isinstance(widget, (ValueWidget, ContainerWidget)):
            widget.changed.connect(lambda: self.changed.emit(self))
        _widget = widget

        if self.labels:
            # no labels for button widgets (push buttons, checkboxes, have their own)
            if not isinstance(widget, (_LabeledWidget, ButtonWidget, Separator)):
                _widget = _LabeledWidget(widget)
                widget.label_changed.connect(self._unify_label_widths)

        if key < 0:
            key += len(self)
        self._list.insert(key, widget)
        # NOTE: if someone has manually mucked around with self.native.layout()
        # it's possible that indices will be off.
        self._widget._mgui_insert_widget(key, _widget)
        self._unify_label_widths()

    def append_preview(self, f: Callable, text: str = "Preview"):
        """Append a preview button to the widget."""
        return append_preview(self, f, text)


def append_preview(self: FunctionGui, f: Callable, text: str = "Preview"):
    """Append a preview button to a FunctionGui widget."""

    btn = PushButton(text=text)
    if isinstance(self[-1], PushButton):
        self.insert(len(self) - 1, btn)
    else:
        self.append(btn)

    @btn.changed.connect
    def _call_preview():
        sig = self.__signature__
        bound = sig.bind()
        bound.apply_defaults()
        return f(*bound.args, **bound.kwargs)

    return f
