from __future__ import annotations
from typing import Callable, TYPE_CHECKING, TypeVar, overload

from macrokit import Mock, Expr
from magicclass.utils import show_messagebox
from magicclass.signature import upgrade_signature
from magicclass._exceptions import Canceled

if TYPE_CHECKING:
    from magicclass._gui import BaseGui

_F = TypeVar("_F", bound=Callable)


@overload
def confirm(
    *,
    text: str | None,
    condition: Callable[..., bool] | str | Mock | Expr | None,
    callback: Callable[[str, BaseGui], None] | None = None,
) -> Callable[[_F], _F]:
    ...


@overload
def confirm(
    f: _F,
    *,
    text: str | None,
    condition: Callable[..., bool] | str | Mock | Expr | None,
    callback: Callable[[str, BaseGui], None] | None = None,
) -> _F:
    ...


def confirm(f=None, *, text=None, condition=None, callback=None):
    """
    Confirm if it is OK to run function in GUI.

    Useful when the function will irreversibly delete or update something in GUI.
    Confirmation will be executed only when function is called in GUI.

    Parameters
    ----------
    text : str, optional
        Confirmation message, such as "Are you sure to run this function?". _Format
        string can also be used here, in which case arguments will be passed. For
        instance, to execute confirmation on function `f(a, b)`, you can use
        format string `"Running with a = {a} and b = {b}"` then confirmation
        message will be "Running with a = 1, b = 2" if `f(1, 2)` is called.
        By default, message will be "Do you want to run {name}?" where "name" is
        the function name.
    condition : callable or str, optional
        Condition of when confirmation will show up. If callable, it must accept
        `condition(self)` and return boolean object. If string, it must be
        evaluable as literal with input arguments as local namespace. For instance,
        function `f(a, b)` decorated by `confirm(condition="a < b + 1")` will
        evaluate `a < b + 1` to check if confirmation is needed. Always true by
        default.
    callback : callable, optional
        Callback function when confirmation is needed. Must take a `str` and a
        `BaseGui` object as inputs. By default, message box will be shown. Useful
        for testing.
    """
    if condition is None:
        condition = lambda x: True
    elif isinstance(condition, (Mock, Expr)):
        condition = str(condition)
    if callback is None:
        callback = _default_confirmation

    def _decorator(method: _F) -> _F:
        _name = method.__name__

        # set text
        if text is None:
            _text = f"Do you want to run {_name}?"
        elif isinstance(text, str):
            _text = text
        else:
            raise TypeError(
                f"The first argument of 'confirm' must be a str but got {type(text)}."
            )
        upgrade_signature(
            method,
            additional_options={
                "confirm": {
                    "text": _text,
                    "condition": condition,
                    "callback": callback,
                }
            },
        )
        return method

    if f is not None:
        return _decorator(f)
    return _decorator


def _default_confirmation(text: str, gui: BaseGui):
    ok = show_messagebox(
        mode="question",
        title="Confirmation",
        text=text,
        parent=gui.native,
    )
    if not ok:
        raise Canceled("Canceled")
