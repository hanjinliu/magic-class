from __future__ import annotations
from functools import partial
from typing import Any, Callable
from types import MethodType
import inspect
from ..signature import get_signature, upgrade_signature


def partial_gui(
    func: Callable,
    *args,
    function_name: str | None = None,
    **kwargs,
):
    options: dict[str, Any] = {}
    if args:
        sig = inspect.signature(func)
        for k, arg in zip(sig.parameters, args):
            options[k] = {"bind": arg}
    if kwargs:
        for k, v in kwargs.items():
            options[k] = {"bind": v}
    if isinstance(func, MethodType):
        _func = _unwrap_method(func)
        options["self"] = {"bind": func.__self__}
    else:
        _func = func
    out = partial(_func)
    out.__name__ = function_name or func.__name__
    upgrade_signature(out, gui_options=options)
    return out


def _unwrap_method(func: MethodType):
    def _unwrapped(*args, **kwargs):
        return func(*args, **kwargs)

    _unwrapped.__name__ = func.__name__
    _unwrapped.__qualname__ = func.__qualname__
    _unwrapped.__annotations__ = func.__annotations__
    _unwrapped.__module__ = func.__module__
    _unwrapped.__doc__ = func.__doc__
    _unwrapped.__signature__ = get_signature(func)
    return _unwrapped
