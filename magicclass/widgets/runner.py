from __future__ import annotations

from typing import TYPE_CHECKING, Callable
import weakref
from magicgui.widgets import PushButton, Container, Label, Select, Dialog, LineEdit
from magicclass.widgets.containers import ScrollableContainer
from macrokit import Macro

if TYPE_CHECKING:
    from magicclass import MagicTemplate


def annotated_button(func: Callable, text: str, desc: str):
    button = PushButton(text=text)
    button.changed.connect(func)
    label = Label(value=desc)
    cnt = Container(widgets=[button, label], layout="horizontal")
    cnt.margins = (0, 0, 0, 0)
    return cnt


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

    def __init__(self):
        super().__init__(labels=False)
        self._magicclass_parent_ref = None

    @property
    def parent_ui(self) -> MagicTemplate:
        return self.__magicclass_parent__._search_parent_magicclass()

    def add_action(self, ranges: int | slice | list[int]) -> CommandRunner:
        """Add (a collection of) action(s)."""
        ui = self.parent_ui
        if isinstance(ranges, list):
            expr = ui.macro.subset(ranges)
        else:
            expr = ui.macro[ranges]
        text = f"Command {len(self)}"
        if isinstance(expr, Macro):
            desc = f"<code>{expr[0]}</code>..."
        else:
            desc = f"<code>{expr}</code>"
        self.append(annotated_button(lambda: expr.eval({"ui": ui}), text, desc))
        return self

    def add_last_action(self) -> CommandRunner:
        """Add the last action of the parent magicclass."""
        return self.add_action(-1)

    def add_action_from_dialog(self) -> CommandRunner:
        ui = self.parent_ui
        select = Select(
            choices=[(f"{i}: {line}", i) for i, line in enumerate(ui.macro)]
        )
        line_text = LineEdit(label="Command name:")
        line_desc = LineEdit(label="Command description:")
        dlg = Dialog(widgets=[select, line_text, line_desc], parent=ui.native)
        if dlg.exec():
            self.add_action(list(select.value))
            text = line_text.value or None
            desc = line_desc.value or None
            self.update_info(-1, text, desc)
        return self

    def update_info(
        self,
        index: int,
        text: str | None = None,
        desc: str | None = None,
        tooltip: str | None = None,
    ) -> CommandRunner:
        if text is not None:
            self[index][0].text = text
        if desc is not None:
            self[index][1].value = desc
        if tooltip is not None:
            self[index][0].tooltip = tooltip
        return self

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
