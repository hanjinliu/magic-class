from __future__ import annotations

from types import MethodType
from typing import Iterator

import inspect
from magicgui.widgets import Widget
from magicclass import MagicTemplate, abstractapi, get_function_gui
from magicclass.fields._fields import _FieldObject
from magicclass._gui._base import MagicGuiBuildError
from magicclass._gui.mgui_ext import PushButtonPlus, Action


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


def _iter_method_with_button(ui: MagicTemplate) -> Iterator[MethodType]:
    for child in ui:
        if isinstance(child, (PushButtonPlus, Action)):
            method = getattr(ui, child.name)
            if callable(method) and not isinstance(method, abstractapi):
                yield method
        if isinstance(child, MagicTemplate):
            yield from _iter_method_with_button(child)


def _iter_method_with_button_or_gui(
    ui: MagicTemplate,
) -> Iterator[MethodType | MagicTemplate]:
    yield ui
    for child in ui:
        if isinstance(child, (PushButtonPlus, Action)):
            method = getattr(ui, child.name)
            if callable(method) and not isinstance(method, abstractapi):
                yield method
        if isinstance(child, MagicTemplate):
            yield from _iter_method_with_button_or_gui(child)
            yield child


def check_function_gui_buildable(ui: MagicTemplate, skips: list = []):
    """Assert that all methods in ``ui`` can be built into GUI."""

    failed = []
    for method in _iter_method_with_button(ui):
        if not method in skips:
            try:
                fgui = get_function_gui(method)
            except MagicGuiBuildError as e:
                failed.append(("Error on building FunctionGui.", method, str(e)))
                continue

            try:
                method_sig = getattr(method, "__signature__", None)
                sig = fgui.__signature__
                if method_sig is None:
                    method_sig = sig
                kwargs = {}
                for param in method_sig.parameters.values():
                    if param.default is param.empty and "bind" in param.options:
                        kwargs[param.name] = object()  # dummy object
            except Exception as e:
                failed.append(
                    ("Untrackable error on refering signature.", method, str(e))
                )
                continue

            try:
                sig.bind()  # raise TypeError if not correctly defined
            except TypeError as e:
                failed.append(("Wrong function signature.", method, str(e)))
            except Exception as e:
                failed.append(("Untrackable error.", method, str(e)))

    if failed:
        txt = "\n".join(f"{obj!r}: {typ} {msg}" for typ, obj, msg in failed)
        raise AssertionError(txt)


def check_tooltip(ui: MagicTemplate):
    from magicclass.utils import Tooltips

    failed = []
    for obj in _iter_method_with_button_or_gui(ui):
        tooltips = Tooltips(obj)
        if isinstance(obj, MagicTemplate):
            for attr in tooltips.attributes:
                if not isinstance(
                    getattr(ui.__class__, attr, None), (Widget, _FieldObject)
                ):
                    failed.append(
                        (obj, f"Widget or field named {attr!r} not found in {ui!r}")
                    )
        else:
            for arg in tooltips.parameters:
                params = set(inspect.signature(obj).parameters.keys())
                if arg not in params:
                    failed.append((obj, f"{arg!r} not found in method {obj!r}"))

    if failed:
        txt = "\n".join(f"{obj!r}: {msg}" for obj, msg in failed)
        raise AssertionError(f"Tooltip check failed:\n\n{txt}")
