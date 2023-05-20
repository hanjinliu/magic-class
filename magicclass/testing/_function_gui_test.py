from __future__ import annotations

from typing import Callable, Generic, TypeVar
from typing_extensions import ParamSpec

from magicgui.widgets import PushButton, CheckBox

from magicclass import get_function_gui
from magicclass.signature import get_additional_option


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
    def __init__(self, method: Callable[_P, _R]):
        self._fgui = get_function_gui(method)
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
        return self._prev_func is not None

    @property
    def has_confirmation(self) -> bool:
        return self._conf_dict is not None

    def click_preview(self):
        if not self.has_preview:
            raise RuntimeError("No preview function found.")
        if self._fgui._auto_call:
            idx = -1
        else:
            idx = -2
        prev_widget = self._fgui[idx]
        if self._prev_auto_call:
            assert isinstance(prev_widget, CheckBox)
            prev_widget.value = not prev_widget.value
        else:
            assert isinstance(prev_widget, PushButton)
            prev_widget.changed.emit(True)

    def update_parameters(self, **kwargs):
        self._fgui.update(**kwargs)

    def call(self, *args: _P.args, **kwargs: _P.kwargs):
        if not self.has_confirmation:
            return self._fgui(*args, **kwargs)
        cb = self._conf_dict["callback"]
        self._conf_dict["callback"] = self._mock_confirmation
        try:
            out = self._fgui(*args, **kwargs)
        finally:
            self._conf_dict["callback"] = cb
        return out

    @property
    def confirm_count(self) -> int:
        return self._n_confirm

    @property
    def call_count(self) -> int:
        return self._fgui.call_count

    def _mock_confirmation(self, *_, **__):
        self._n_confirm += 1
