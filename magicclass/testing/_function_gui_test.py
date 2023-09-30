from __future__ import annotations

from typing import Callable, Generic, TypeVar, TYPE_CHECKING
from typing_extensions import ParamSpec
from contextlib import contextmanager

from magicgui.widgets import PushButton, CheckBox, FunctionGui

from magicclass import get_function_gui
from magicclass._exceptions import unwrap_errors
from magicclass.signature import get_additional_option

if TYPE_CHECKING:
    from magicclass._gui import BaseGui


class MockConfirmation:
    """Class used for confirmation test."""

    def __init__(self):
        self.text = None
        self.gui = None

    def __call__(self, text, gui):
        self.text = text
        self.gui = gui

    @property
    def value(self):
        return self.text, self.gui

    def assert_value(self, text=None, gui=None):
        if text is None and gui is None:
            assert self.text is not None and self.gui is not None
        elif text is None:
            assert self.gui is gui
        elif gui is None:
            assert self.text == text
        else:
            assert self.value == (text, gui)

    def assert_not_called(self):
        assert self.text is None and self.gui is None


_P = ParamSpec("_P")
_R = TypeVar("_R")


class FunctionGuiTester(Generic[_P]):
    """Testing class for magicclass-integrated FunctionGui."""

    def __init__(self, method: Callable[_P, _R]):
        self._fgui = get_function_gui(method)
        # NOTE: if the widget is in napari etc., choices depend on the parent.
        ui: BaseGui = method.__self__
        self._magicclass_gui = ui
        self._fgui.native.setParent(ui.native, self._fgui.native.windowFlags())
        self._fgui.reset_choices()
        self._method = method
        if prev := get_additional_option(method, "preview", None):
            _, self._prev_auto_call, self._prev_func = prev
        else:
            self._prev_auto_call = False
            self._prev_func = None
        if conf := get_additional_option(method, "confirm", None):
            self._conf_dict = conf
        else:
            self._conf_dict = None
        self._n_confirm = 0

    @property
    def has_preview(self) -> bool:
        """True if the method has preview function."""
        return self._prev_func is not None

    @property
    def has_confirmation(self) -> bool:
        """True if the method has confirmation function."""
        return self._conf_dict is not None

    def click_preview(self):
        """Emulate the preview button click."""
        if not self.has_preview:
            raise RuntimeError("No preview function found.")
        if self._fgui._auto_call:
            idx = -1
        else:
            idx = -2
        prev_widget = self._fgui[idx]
        if self._prev_auto_call:
            assert isinstance(prev_widget, CheckBox)
            with self.stream_error():
                prev_widget.value = not prev_widget.value
        else:
            assert isinstance(prev_widget, PushButton)
            with self.stream_error():
                prev_widget.changed.emit(True)

    def update_parameters(self, **kwargs):
        """Update the parameters of the function GUI."""
        with self.stream_error():
            self._fgui.update(**kwargs)

    def call(self, *args: _P.args, **kwargs: _P.kwargs):
        """Call the method as if it is called from the GUI."""
        with self.stream_error():
            if not self.has_confirmation:
                return self._fgui(*args, **kwargs)
            cb = self._conf_dict["callback"]
            self._conf_dict["callback"] = self._mock_confirmation
            try:
                out = self._fgui(*args, **kwargs)
            finally:
                self._conf_dict["callback"] = cb
            return out

    @contextmanager
    def stream_error(self):
        """Stream the error message to stderr not to raise in GUI."""
        with self._magicclass_gui.config_context(error_mode="stderr"):
            try:
                yield
            except Exception as e:
                raise unwrap_errors(e)

    @property
    def confirm_count(self) -> int:
        """Number of times the confirmation is called."""
        return self._n_confirm

    @property
    def call_count(self) -> int:
        """Number of times the method is called."""
        return self._fgui.call_count

    @property
    def gui(self) -> FunctionGui:
        """The FunctionGui instance."""
        return self._fgui

    def _mock_confirmation(self, *_, **__):
        self._n_confirm += 1
