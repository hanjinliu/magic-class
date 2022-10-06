from __future__ import annotations
import functools
from typing import Any, TYPE_CHECKING
from types import MethodType
import inspect
from magicgui.widgets import EmptyWidget
from ..signature import get_signature, upgrade_signature

if TYPE_CHECKING:
    from ..signature import MagicMethodSignature


class partial(functools.partial):
    """
    Partialize a function and its signature.

    This object is similar to ``functools.partial``, but it also update
    widget options to build magicgui widget with subset of widgets. More
    precisely, partializing ``x=0`` will add option
    ``x={"bind": 0, "widget_type": EmptyWidget}``.

    Parameters
    ----------
    func : Callable
        Callable object to be partialized.
    function_text : str, optional
        Text that will be used in the button or action in magic class.

    Examples
    --------
    Suppose you have a magic class.

    >>> @magicclass
    >>> class A:
    >>>     def f(self, i: int): ...

    You can partialize method ``f``.

    >>> ui = A()
    >>> ui.append(partial(ui.f, i=1))
    """

    __signature__: MagicMethodSignature

    def __new__(cls, func, /, *args, function_text: str | None = None, **kwargs):
        # prepare widget options
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

        # construct partial object
        self = functools.partial.__new__(cls, _func, *args, **kwargs)

        # keyword only arguments have to be replaced because "sig.bind" receives
        # all the values.
        sig = get_signature(self)

        self.__signature__ = sig.replace(
            parameters=[
                p.replace(kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
                for p in sig.parameters.values()
            ]
        )

        self.__name__ = _func.__name__
        if function_text is not None:
            caller_options = {"text": function_text}
        else:
            caller_options = {}

        upgrade_signature(self, gui_options=options, caller_options=caller_options)
        return self


class partialmethod(functools.partialmethod):
    __signature__: MagicMethodSignature

    def __init__(self, func, /, *args, function_text: str | None = None, **kwargs):
        # prepare widget options
        options: dict[str, Any] = {}
        if args:
            sig = inspect.signature(func)
            for k, arg in zip(sig.parameters, args):
                options[k] = {"widget_type": EmptyWidget}
        if kwargs:
            for k, v in kwargs.items():
                options[k] = {"widget_type": EmptyWidget}

        if isinstance(func, MethodType):
            _func = _unwrap_method(func)
            options["self"] = {"bind": func.__self__, "widget_type": EmptyWidget}
        else:
            _func = func

        # construct partial object
        super().__init__(_func, *args, **kwargs)
        sig = get_signature(partial(_func, *args, **kwargs))  # safely assign defaults
        self.__signature__ = sig.replace(
            parameters=[
                p.replace(kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
                for p in sig.parameters.values()
            ]
        )

        self.__name__ = _func.__name__
        if function_text is not None:
            caller_options = {"text": function_text}
        else:
            caller_options = {}

        upgrade_signature(self, gui_options=options, caller_options=caller_options)

    def __call__(self, *args: Any, **kwargs: Any):
        # needed to be defined because magicclass checks callable
        raise TypeError("partialmethod object is not callable")


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
