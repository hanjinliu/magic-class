from __future__ import annotations
from typing import Callable, TYPE_CHECKING
from macrokit import Expr
from magicgui.widgets import PushButton

if TYPE_CHECKING:
    from .._gui import MenuGuiBase
    from .._gui._function_gui import FunctionGui


def call_recent_menu(
    func: Callable,
    *,
    name: str | None = None,
    text: str | Callable[..., str] | None = None,
    max: int = 12,
) -> MenuGuiBase:
    """
    Create a "call recent" menu.

    This function returns a magicmenu object that calls ``func`` with recent arguments.

    >>> @magicclass
    >>> class A:
    >>>     @magicmenu
    >>>     class File:
    >>>         def open_file(self, path: Path): ...
    >>>         menu = call_recent_menu(f, name="open recent")

    Parameters
    ----------
    func : Callable
        Target function.
    name : str, optional
        Name of the magicmenu object.
    text : str or Callable[..., str], optional
        Specify how to display recent arguments when ``func(**kwargs)`` is called. If
        ``text`` is a string, ``text.format(**kwargs)`` will be used. If ``text`` is a
        callable, ``text(**kwargs)`` will be used.
    max : int, default is 12
        Maximum number of history.

    Returns
    -------
    MenuGuiBase
        magicmenu object.
    """
    from ..core import magicmenu
    from .._gui import MagicTemplate
    from ..wrappers import mark_on_called
    from ..functools._partial import partial

    # dispatch text type
    if text is None:
        _make_text = _default_fmt
    elif isinstance(text, str):
        _make_text = text.format
    elif callable(text):
        _make_text = text
    else:
        raise TypeError("text must be a string or a callable if given.")

    if name is None:
        name = f"Recent call of {func.__name__}"

    @magicmenu(name=name)
    class _Menu(MagicTemplate):
        def _append_history(self, mgui: FunctionGui):
            kwargs = {
                wdt.name: wdt.value for wdt in mgui if not isinstance(wdt, PushButton)
            }
            text = _make_text(**kwargs)
            pf = partial(mgui._function, **kwargs).set_options(text=text)

            for i, a in enumerate(self._list):
                if a.text == text:
                    del self[i]
                    break
            self.insert(0, pf)
            if len(self) > max:
                self.pop(-1)
            return None

    menu = _Menu()
    mark_on_called(func)(menu._append_history)
    return menu


def _default_fmt(**kwargs) -> str:
    if len(kwargs) == 0:
        return ""
    elif len(kwargs) == 1:
        return str(kwargs.popitem()[1])
    else:
        exprs = Expr._convert_args((), kwargs)
        return ", ".join(f"{expr}" for expr in exprs)
