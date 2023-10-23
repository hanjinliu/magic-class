from __future__ import annotations
from types import GeneratorType
from typing import Any, TYPE_CHECKING, Callable, TypeVar
from typing_extensions import ParamSpec
import re
from psygnal import Signal
from magicgui.widgets import PushButton, CheckBox, FunctionGui
from magicgui.widgets.bases import (
    ValueWidget,
    ButtonWidget,
    ContainerWidget,
)
from magicgui.widgets._concrete import _LabeledWidget

from magicclass.widgets import Separator

if TYPE_CHECKING:
    from magicgui.widgets import Widget

_P = ParamSpec("_P")
_R = TypeVar("_R")


class FunctionGuiPlus(FunctionGui[_P, _R]):
    """FunctionGui class with a parameter recording functionality etc."""

    _dialog_widget = None
    _initialized_for_magicclass = False
    calling = Signal(object)

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        update_widget: bool = bool(kwargs.pop("update_widget", False))
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
        self.calling.emit(self)  # 3. calling signal
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
            from magicgui.type_map import type2callback

            for callback in type2callback(return_type):
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


class PreviewContext:
    def __init__(self):
        self._generator = None

    def enter(self, gen: GeneratorType):
        """Start preview context defined by the given generator."""
        if not isinstance(gen, GeneratorType):
            raise TypeError("Must be a generator.")

        self._generator = gen
        next(self._generator)
        return None

    def send(self, active: bool) -> bool:
        """Advance the preview context and return True if it is still active."""
        if self._generator is None:
            return False
        try:
            self._generator.send(active)
        except StopIteration:
            return False
        return True

    def exit(self):
        if self._generator is None:
            return None
        if self.send(active=False):
            import warnings

            warnings.warn(
                "Contextmanager did not exit on function call. Please "
                "make sure it yields only once, like functions decorated with "
                "@contextmanager."
            )
        self._generator = None
        return None


def _append_preview(self: FunctionGui, f: Callable, text: str = "Preview"):
    """Append a preview button to a FunctionGui widget."""
    btn = PushButton(text=text)

    context = PreviewContext()

    if _prev_context := getattr(f, "_preview_context", None):
        _prev_context_method = _prev_context.__get__(f.__self__)
    else:
        _prev_context_method = _dummy_context_manager

    if isinstance(self[-1], PushButton):
        self.insert(len(self) - 1, btn)
    else:
        self.append(btn)

    @btn.changed.connect
    def _call_preview():
        sig = self.__signature__
        bound = sig.bind()
        bound.apply_defaults()
        _args = bound.args
        _kwargs = bound.kwargs
        with f.__self__.macro.blocked():
            context.exit()
            generator = _prev_context_method(*_args, **_kwargs)
            try:
                context.enter(generator)
            except StopIteration as e:
                context.exit()
                raise RuntimeError(f"Preview function {f!r} raised StopIteration: {e}")
        return f(*_args, **_kwargs)

    if _prev_context_method is not _dummy_context_manager:
        if not isinstance(self, FunctionGuiPlus):
            raise NotImplementedError(
                "during_preview context is not implemented for FunctionGui."
            )

        self.calling.connect(context.exit)

    return f


def _append_auto_call_preview(self: FunctionGui, f: Callable, text: str = "Preview"):
    """Append a preview check box to a FunctionGui widget."""

    cbox = CheckBox(value=False, text=text, gui_only=True)

    generator = None
    context = PreviewContext()

    if _prev_context := getattr(f, "_preview_context", None):
        _prev_context_method = _prev_context.__get__(f.__self__)
    else:
        _prev_context_method = _dummy_context_manager

    if isinstance(self[-1], PushButton):
        self.insert(len(self) - 1, cbox)
    else:
        self.append(cbox)

    @self.changed.connect
    def _call_preview():
        nonlocal generator, context
        # NOTE: if the preview function trigger the changed signal, this function
        # may call enter() twice without closing the previous context.
        with self.changed.blocked():
            if cbox.value:
                sig = self.__signature__
                if not self._call_button.enabled:
                    # Button is disabled, such as when the call button is clicked.
                    context.exit()
                    return
                bound = sig.bind()
                bound.apply_defaults()
                _args = bound.args
                _kwargs = bound.kwargs
                with f.__self__.macro.blocked():
                    context.send(active=True)
                    generator = _prev_context_method(*_args, **_kwargs)
                    try:
                        context.enter(generator)
                    except StopIteration as e:
                        context.exit()
                        raise RuntimeError(
                            f"Preview function {f!r} raised StopIteration: {e}"
                        )
                    return f(*_args, **_kwargs)
            else:
                with f.__self__.macro.blocked():
                    context.exit()  # reset the original state

    if _prev_context_method is not _dummy_context_manager:
        if not isinstance(self, FunctionGuiPlus):
            raise NotImplementedError(
                "during_preview context is not implemented for FunctionGui."
            )

        self.calling.connect(context.exit)

        @self.called.connect
        def _disable_auto_call():
            cbox.value = False

    return f


def _dummy_context_manager(*args, **kwargs):
    """An empty context manager."""
    yield
