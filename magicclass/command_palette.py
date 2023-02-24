# Built-in command palette for magicclass
# Currently it is not very customizable.

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable
from qt_command_palette import get_palette
from magicclass._gui import BaseGui
from magicclass._gui.mgui_ext import Clickable, is_clickable

if TYPE_CHECKING:
    from qt_command_palette._api import CommandPalette

_PALETTES: dict[int, CommandPalette] = {}


def exec_command_palette(gui: BaseGui):
    """
    Register all the methods available from GUI to the command palette.

    >>> from magicclass import magicclass, bind_key
    >>> from magicclass.command_palette import exec_command_palette
    >>> @magicclass
    >>> class A:
    ...     def f(self, x: int): ...
    ...     def g(self): ...
    ...     @bind_key("F1")
    ...     def _exec_command_palette(self):
    ...         exec_command_palette(self)

    Parameters
    ----------
    gui : magic-class
        Magic-class instance.
    """
    _id = id(gui)
    if _id in _PALETTES:
        return _PALETTES[_id].show_widget(gui.native)
    name = f"magicclass-{id(gui)}"
    palette = get_palette(name)

    for parent, wdt in _iter_executable(gui):
        _qualname = type(parent).__qualname__
        palette.register(
            lambda: wdt.clicked.emit(),
            title=_qualname,
            desc=wdt.text,
            when=lambda: wdt.enabled,
        )
    _PALETTES[_id] = palette
    palette.install(gui.native)
    return palette.show_widget(gui.native)


def _iter_executable(gui: BaseGui) -> Iterable[tuple[BaseGui, Clickable]]:
    for child in gui.__magicclass_children__:
        yield from _iter_executable(child)
    for wdt in gui:
        if is_clickable(wdt):
            yield gui, wdt
        elif isinstance(wdt, BaseGui):
            if wdt in gui.__magicclass_children__:
                continue
            yield from _iter_executable(wdt)
