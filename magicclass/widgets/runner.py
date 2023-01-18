from __future__ import annotations
from pathlib import Path

from typing import TYPE_CHECKING, Any, Callable, Union
import weakref
from macrokit import Expr, Symbol, parse
from magicgui.widgets import PushButton
from magicclass.widgets.containers import ScrollableContainer

if TYPE_CHECKING:
    from magicclass import MagicTemplate

    _ActionLike = Union[Callable[[], Any], Expr]


def _create_button(func: Callable, text: str, tooltip: str):
    button = PushButton(text=text, tooltip=tooltip)
    button.changed.connect(func)
    return button


class CommandRunner(ScrollableContainer):
    """
    A command runner widget for magicclass.

    This widget is a collection of buttons that run the commands derived from the
    viewer. This widget can auto-detect its parent magicclass via the attribute
    ``__magicclass_parent__``.

    Examples
    --------
    >>> from magicclass import magicclass, field
    >>> from magicclass.widgets import CommandRunner
    >>> @magicclass
    >>> class A:
    ...     cmd = field(CommandRunner)
    ...     def f(self, x: int):
    ...         print(x)
    ...     def g(self):
    ...         print("g")
    >>> ui = A()
    >>> ui.show()

    After clicking the button "g", you can add the command ``ui.g()`` by calling
    ``ui.cmd.add_last_action()``.
    """

    def __init__(self, **kwargs):
        super().__init__(labels=False, **kwargs)
        self._magicclass_parent_ref = None

    @property
    def parent_ui(self) -> MagicTemplate:
        return self.__magicclass_parent__._search_parent_magicclass()

    def add_action(
        self, slot: _ActionLike, text: str = None, tooltip: str = None
    ) -> CommandRunner:
        """Add a function or an expression as an action."""
        if isinstance(slot, Expr):
            ns = {Symbol.var("ui"): self.parent_ui}
            if (viewer := self.parent_ui.parent_viewer) is not None:
                ns.setdefault(Symbol.var("viewer"), viewer)
            slot = lambda: slot.eval(ns)
            slot.__doc__ = f"<b><code>{slot}</code></b>"
        elif not callable(slot):
            raise TypeError(f"slot must be callable or an Expr, got {type(slot)}")
        if text is None:
            text = f"Command {len(self)}"
        if tooltip is None:
            tooltip = getattr(slot, "__doc__", None)
        tooltip = tooltip.replace("\n", "<br>")
        self.append(_create_button(slot, text, tooltip))
        return self

    def add_file(self, path: str | Path | bytes) -> CommandRunner:
        with open(path) as f:
            expr = parse(f.read())
        return self.add_action(expr)

    @property
    def __magicclass_parent__(self) -> MagicTemplate | None:
        """Return parent magic class if exists."""
        if self._magicclass_parent_ref is None:
            return None
        parent = self._magicclass_parent_ref()
        return parent

    @__magicclass_parent__.setter
    def __magicclass_parent__(self, parent) -> None:
        if parent is None:
            return
        self._magicclass_parent_ref = weakref.ref(parent)
