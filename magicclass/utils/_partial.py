from __future__ import annotations
from functools import partial
from typing import Any, Callable
from types import MethodType
import inspect
from magicgui.widgets import EmptyWidget
from ..signature import get_signature, upgrade_signature


def partial_gui(
    func: Callable,
    *args,
    function_text: str | None = None,
    **kwargs,
):
    """
    Partialize a function and its signature.

    This function is similar to ``functools.partial``, but it also update
    widget options to build magicgui widget with subset of widgets. More
    precisely, partializing ``x=0`` will add option ``x={"bind": 0}``.

    Parameters
    ----------
    func : Callable
        Callable object to be partialized.
    function_text : str, optional
        Text that will be used in the button or action in magic class.

    Returns
    -------
    functools.partial
        Partial object with updated signature.

    Examples
    --------
    Suppose you have a magic class.

    >>> @magicclass
    >>> class A:
    >>>     def f(self, i: int): ...

    You can partialize method ``f``.

    >>> ui = A()
    >>> ui.append(partial_gui(ui.f, i=1))
    """
    options: dict[str, Any] = {}
    if args:
        sig = inspect.signature(func)
        for k, arg in zip(sig.parameters, args):
            options[k] = {"bind": arg, "widget_type": EmptyWidget}
    if kwargs:
        for k, v in kwargs.items():
            options[k] = {"bind": v, "widget_type": EmptyWidget}
    if isinstance(func, MethodType):
        _func = _unwrap_method(func)
        options["self"] = {"bind": func.__self__, "widget_type": EmptyWidget}
    else:
        _func = func
    out = partial(_func)
    out.__name__ = _func.__name__
    if function_text is not None:
        caller_options = {"text": function_text}
    else:
        caller_options = {}
    upgrade_signature(out, gui_options=options, caller_options=caller_options)
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
