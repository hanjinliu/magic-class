from __future__ import annotations

from types import MethodType
from typing import Iterator
import inspect

from magicgui.widgets import Widget

from magicclass import MagicTemplate, abstractapi, get_function_gui
from magicclass.fields._fields import _FieldObject
from magicclass._gui._base import MagicGuiBuildError
from magicclass._gui.mgui_ext import PushButtonPlus, Action


def _iter_method_with_button(ui: MagicTemplate) -> Iterator[MethodType]:
    processed = set()
    for child in ui:
        if id(child) in processed:
            continue
        processed.add(id(child))
        if isinstance(child, (PushButtonPlus, Action)):
            method = getattr(ui, child.name)
            if callable(method) and not isinstance(method, abstractapi):
                yield method
        if isinstance(child, MagicTemplate):
            yield from _iter_method_with_button(child)

    for child in ui.__magicclass_children__:
        if id(child) in processed:
            continue
        processed.add(id(child))
        yield from _iter_method_with_button(child)


def _iter_method_with_button_or_gui(
    ui: MagicTemplate,
) -> Iterator[MethodType | MagicTemplate]:
    yield ui
    processed = set()
    for child in ui:
        if id(child) in processed:
            continue
        processed.add(id(child))

        if isinstance(child, (PushButtonPlus, Action)):
            method = getattr(ui, child.name)
            if callable(method) and not isinstance(method, abstractapi):
                yield method
        if isinstance(child, MagicTemplate):
            yield from _iter_method_with_button_or_gui(child)

    for child in ui.__magicclass_children__:
        if id(child) in processed:
            continue
        processed.add(id(child))
        yield from _iter_method_with_button_or_gui(child)


def _qualname(obj: MethodType | type):
    try:
        qualname = obj.__qualname__
    except Exception:
        return str(obj)
    if not isinstance(qualname, str):
        return str(obj)
    return qualname.rsplit("<locals>", 1)[-1]


def check_function_gui_buildable(ui: MagicTemplate, skips: list = []):
    """Assert that all methods in ``ui`` can be built into GUI."""

    failed = []
    for method in _iter_method_with_button(ui):
        if not method in skips:
            try:
                fgui = get_function_gui(method)
            except MagicGuiBuildError as e:
                failed.append(
                    ("Error on building FunctionGui.", _qualname(method), str(e))
                )
                continue
            try:
                sig = fgui.__signature__
            except Exception as e:
                failed.append(
                    ("Failed to get FunctionGui signature.", _qualname(method), str(e))
                )
                continue
            try:
                method_sig = getattr(method, "__signature__", None)
                if method_sig is None:
                    method_sig = sig
                kwargs = {}
                for param in method_sig.parameters.values():
                    if "bind" in param.options:
                        kwargs[param.name] = object()  # dummy object
            except Exception as e:
                failed.append(
                    (
                        "Untrackable error on refering signature.",
                        _qualname(method),
                        str(e),
                    )
                )
                continue

            try:
                sig.bind(**kwargs)  # raise TypeError if not correctly defined
            except TypeError as e:
                failed.append(("Wrong function signature.", _qualname(method), str(e)))
            except Exception as e:
                failed.append(("Untrackable error.", _qualname(method), str(e)))

    if failed:
        txt = "\n".join(f"{_qualname(obj)}: {typ} {msg}" for typ, obj, msg in failed)
        raise AssertionError(txt)


def check_tooltip(ui: MagicTemplate):
    from magicclass.utils import Tooltips

    failed = []
    for obj in _iter_method_with_button_or_gui(ui):
        tooltips = Tooltips(obj)
        if isinstance(obj, MagicTemplate):
            for attr in tooltips.attributes:
                if not hasattr(obj, attr):
                    failed.append(
                        (obj, f"{_qualname(obj)} does not have attribute {attr!r}.")
                    )
                elif not isinstance(
                    getattr(obj.__class__, attr, None), (Widget, _FieldObject)
                ):
                    failed.append(
                        (
                            obj,
                            f"Widget or field named {attr!r} not found in {_qualname(obj)}",
                        )
                    )
        else:
            for arg in tooltips.parameters:
                params = set(inspect.signature(obj).parameters.keys())
                if arg not in params:
                    failed.append(
                        (obj, f"{arg!r} not found in method {_qualname(obj)}")
                    )

    if failed:
        txt = "\n".join(f"{_qualname(obj)}: {msg}" for obj, msg in failed)
        raise AssertionError(f"Tooltip check failed:\n\n{txt}")
