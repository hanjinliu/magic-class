from __future__ import annotations
from functools import wraps
from typing import Callable, Iterable, Union, TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from magicgui.widgets.bases import ButtonWidget
    from magicclass._gui import BaseGui
    from magicclass._gui.mgui_ext import Action

nStrings = Union[str, Iterable[str]]


def click(
    enables: nStrings | None = None,
    disables: nStrings | None = None,
    enabled: bool = True,
    shows: nStrings | None = None,
    hides: nStrings | None = None,
    visible: bool = True,
):
    """
    Set options of push buttons related to button clickability.

    Parameters
    ----------
    enables : str or iterable of str, optional
        Enables other button(s) in this list when clicked.
    disables : str or iterable of str, optional
        Disables other button(s) in this list when clicked.
    enabled : bool, default is True
        The initial clickability state of the button.
    shows : str or iterable of str, optional
        Make other button(s) in this list visible when clicked.
    hides : str or iterable of str, optional
        Make other button(s) in this list invisible when clicked.
    visible: bool, default is True
        The initial visibility of the button.
    """
    enables = _assert_iterable(enables)
    disables = _assert_iterable(disables)
    shows = _assert_iterable(shows)
    hides = _assert_iterable(hides)

    def wrapper(func):
        @wraps(func)
        def f(self, *args, **kwargs):
            out = func(self, *args, **kwargs)
            for button in _iter_widgets(self, enables):
                button.enabled = True
            for button in _iter_widgets(self, disables):
                button.enabled = False
            for button in _iter_widgets(self, shows):
                button.visible = True
            for button in _iter_widgets(self, hides):
                button.visible = False

            return out

        caller_options = {"enabled": enabled, "visible": visible}
        from ..signature import upgrade_signature

        upgrade_signature(f, caller_options=caller_options)
        return f

    return wrapper


def _assert_iterable(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str) or callable(obj):
        obj = [obj]
    return obj


def _iter_widgets(
    self: BaseGui, descriptors: Iterable[list[str]] | Iterable[Callable]
) -> Iterator[ButtonWidget | Action]:
    for f in descriptors:
        if callable(f):
            # A.B.func -> B.func, if self is an object of A.
            f = f.__qualname__.split(self.__class__.__name__)[1][1:]

        if isinstance(f, str):
            *clsnames, funcname = f.split(".")
            # search for parent class that match the description.
            ins = self
            for a in clsnames:
                if a != "":
                    ins = getattr(ins, a)
                else:
                    ins = ins.__magicclass_parent__

            button = ins[funcname]
        else:
            raise TypeError(f"Unexpected type in click decorator: {type(f)}")
        yield button
