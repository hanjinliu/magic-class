from __future__ import annotations
from typing import Any, TYPE_CHECKING, Callable, TypeVar
import re
from magicgui.widgets import PushButton, CheckBox
from magicgui.widgets._concrete import _LabeledWidget
from magicgui.widgets._bases import ValueWidget, ButtonWidget, ContainerWidget
from magicgui.widgets._function_gui import FunctionGui
from psygnal import Signal

from ..widgets import Separator

if TYPE_CHECKING:
    from magicgui.widgets import Widget


_R = TypeVar("_R")


class FunctionGuiPlus(FunctionGui[_R]):
    """FunctionGui class with a parameter recording functionality etc."""

    _dialog_widget = None
    calling = Signal(object)

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

        # 2. Running flag
        # We sometimes want to know if the function is called programmatically or
        # from GUI. The "running" argument is True only when it's called via GUI.
        self.running = True
        self.calling.emit(self)  # 3. calling signal
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

    def append_preview(
        self, f: Callable, text: str = "Preview", auto_call: bool = False
    ):
        """Append a preview button to the widget."""
        return append_preview(self, f, text, auto_call=auto_call)

    def exec_as_dialog(self, parent=None):
        """Show container as a dialog."""
        if self._dialog_widget is None:
            from magicgui.widgets import Dialog

            dlg = Dialog(widgets=[self], labels=False)
            self._dialog_widget = dlg
        else:
            dlg = self._dialog_widget
        dlg.native.setParent(parent.native, dlg.native.windowFlags())
        if self._dialog_widget.exec():
            self()
        return self._dialog_widget

    def reset_choices(self, *_: Any):
        if self.visible:
            return super().reset_choices()
        with self.changed.blocked():
            # in magicclass, magicgui tagged to a button or an action may be invisible,
            # which causes unexpected function call
            super().reset_choices()
        return None


def append_preview(
    self: FunctionGui,
    f: Callable,
    text: str = "Preview",
    auto_call: bool = False,
):
    if auto_call:
        return _append_auto_call_preview(self, f, text)
    else:
        return _append_preview(self, f, text)


def _append_preview(self: FunctionGui, f: Callable, text: str = "Preview"):
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


def _append_auto_call_preview(self: FunctionGui, f: Callable, text: str = "Preview"):
    """Append a preview check box to a FunctionGui widget."""
    import warnings

    cbox = CheckBox(value=False, text=text, gui_only=True)

    generator = None

    if _prev_context := getattr(f, "_preview_context", None):
        _prev_context_method = _prev_context.__get__(f.__self__)

        @cbox.changed.connect
        def _try_context(checked: bool):
            nonlocal generator

            if checked:
                sig = self.__signature__
                bound = sig.bind()
                bound.apply_defaults()
                generator = _prev_context_method(*bound.args, **bound.kwargs)
                next(generator)
            else:
                try:
                    next(generator)
                except StopIteration:
                    pass
                else:
                    warnings.warn(
                        f"{_prev_context} did not exit in the proper timing. Please "
                        "make sure it yields only once, like functions decorated with "
                        "@contextmanager."
                    )
                generator = None
            return

        @self.called.connect
        def _close_context():
            nonlocal generator
            if generator is not None:
                try:
                    next(generator)
                except StopIteration:
                    pass
                else:
                    warnings.warn(
                        f"{_prev_context} did not exit on function call. Please "
                        "make sure it yields only once, like functions decorated with "
                        "@contextmanager."
                    )
                generator = None

    if isinstance(self[-1], PushButton):
        self.insert(len(self) - 1, cbox)
    else:
        self.append(cbox)

    @self.changed.connect
    def _call_preview():
        sig = self.__signature__
        if cbox.value:
            bound = sig.bind()
            bound.apply_defaults()
            return f(*bound.args, **bound.kwargs)

    return f
