from __future__ import annotations
import sys
import functools
from typing import Any, TYPE_CHECKING
import inspect
from magicgui.widgets import EmptyWidget
from magicclass.signature import get_signature, upgrade_signature

if TYPE_CHECKING:
    from magicclass.signature import MagicMethodSignature

_PARTIALIZE = {"gui_only": True, "widget_type": EmptyWidget, "visible": False}


class partial(functools.partial):
    """
    Partialize a function and its signature.

    This object is similar to `functools.partial`, but it also update widget options to
    build magicgui widget with subset of widgets. More precisely, partializing `x=0`
    will add option `x={"gui_only": True, "widget_type": EmptyWidget,
    "visible": False}`.

    Parameters
    ----------
    func : Callable
        Callable object to be partialized.

    Examples
    --------
    Suppose you have a magic class.

    >>> @magicclass
    >>> class A:
    >>>     def f(self, i: int): ...

    You can partialize method `f`.

    >>> ui = A()
    >>> ui.append(partial(ui.f, i=1))
    """

    __signature__: MagicMethodSignature

    def __new__(cls, func, /, *args, **kwargs):
        # prepare widget options
        options: dict[str, Any] = {}
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        for name in bound.arguments.keys():
            options[name] = _PARTIALIZE

        # construct partial object
        self = functools.partial.__new__(cls, func, *args, **kwargs)
        self.__signature__ = get_signature(self)
        self.__name__ = func.__name__

        upgrade_signature(self, gui_options=options)
        return self

    def set_options(
        self,
        text: str | None = None,
        **kwargs,
    ):
        """Set options for the buttons or actions."""
        kwargs.update(text=text)
        upgrade_signature(self, caller_options=kwargs)
        return self


class partialmethod(functools.partialmethod):
    """
    Partialize a method and its signature.

    This object is similar to `functools.partialmethod`, but it also update widget
    options to build magicgui widget with subset of widgets. More precisely,
    partializing `x=0` will add option `x={"gui_only": True, "widget_type": EmptyWidget,
    "visible": False}`.

    Parameters
    ----------
    func : Callable
        Callable object to be partialized.

    Examples
    --------

    >>> @magicclass
    >>> class A:
    ...     def f(self, i: int): ...
    ...     g = partialmethod(f, i=1)

    """

    __signature__: MagicMethodSignature

    if sys.version_info < (3, 14):

        def __init__(self, func, /, *args, **kwargs):
            # prepare widget options
            options: dict[str, Any] = {}
            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            for name in bound.arguments.keys():
                options[name] = _PARTIALIZE

            # construct partial object
            super().__init__(func, *args, **kwargs)
            self.__signature__ = get_signature(partial(func, *args, **kwargs))
            self.__name__ = func.__name__

            upgrade_signature(self, gui_options=options)

    else:

        def __new__(cls, func, /, *args, **kwargs):
            # prepare widget options
            options: dict[str, Any] = {}
            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            for name in bound.arguments.keys():
                options[name] = _PARTIALIZE

            # construct partial object
            self = super().__new__(cls, func, *args, **kwargs)
            self.__signature__ = get_signature(partial(func, *args, **kwargs))
            self.__name__ = func.__name__

            upgrade_signature(self, gui_options=options)
            return self

    def __call__(self, *args: Any, **kwargs: Any):
        # needed to be defined because magicclass checks callable
        raise TypeError("partialmethod object is not callable")

    def __set_name__(self, owner, name):
        self.__signature__.caller_options.setdefault("text", name.replace("_", " "))

    def set_options(
        self,
        text: str | None = None,
        **kwargs,
    ):
        """Set options for the buttons or actions."""
        kwargs.update(text=text)
        upgrade_signature(self, caller_options=kwargs)
        return self
