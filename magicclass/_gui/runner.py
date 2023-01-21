from __future__ import annotations
from pathlib import Path

from typing import TYPE_CHECKING, Any, Callable, Iterator, Union, Sequence
import weakref

from qtpy import QtWidgets as QtW
from macrokit import Expr, Symbol, parse
from magicclass._gui.mgui_ext import Action


if TYPE_CHECKING:
    from magicclass import MagicTemplate

    _ActionLike = Union[Callable[[], Any], Expr]


class CommandRunnerMenu(Sequence[Action]):
    def __init__(
        self,
        title: str,
        parent: QtW.QWidget = None,
        magicclass_parent: MagicTemplate = None,
    ):
        self._native = QtW.QMenu(title, parent)
        self.native.setToolTipsVisible(True)
        self.__magicclass_parent__ = magicclass_parent
        self._command_actions: list[Action] = []

    @property
    def native(self) -> QtW.QMenu:
        return self._native

    @property
    def parent_ui(self) -> MagicTemplate:
        return self.__magicclass_parent__._search_parent_magicclass()

    def __getitem__(self, index: int) -> Action:
        return self._command_actions[index]

    def __len__(self) -> int:
        return len(self._command_actions)

    def __iter__(self) -> Iterator[Action]:
        return iter(self._command_actions)

    def add_action(
        self, slot: _ActionLike, text: str = None, tooltip: str = None
    ) -> CommandRunnerMenu:
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

        action = Action(text=text)
        action.tooltip = tooltip
        action.native.triggered.connect(slot)
        self.native.addAction(action.native)
        self._command_actions.append(action)
        return self

    def add_file(self, path: str | Path | bytes) -> CommandRunnerMenu:
        """Add a executable file as an action."""
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
