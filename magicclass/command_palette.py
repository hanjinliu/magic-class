# Built-in command palette for magicclass
# Currently it is not very customizable.

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable
from typing_extensions import Literal
from qt_command_palette import get_palette
from magicclass._gui import BaseGui
from magicclass._gui.class_gui import ClassGuiBase
from magicclass._gui.mgui_ext import Clickable, is_clickable

if TYPE_CHECKING:
    from qt_command_palette._api import CommandPalette

_PALETTES: dict[int, CommandPalette] = {}


def exec_command_palette(
    gui: BaseGui,
    alignment: Literal["parent", "screen"] = "parent",
):
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
    alignment : "parent" or "screen", default is "parent"
        How to align the command palette.
    """
    _id = id(gui)
    if _id in _PALETTES:
        return _PALETTES[_id].show_widget(gui.native)
    name = f"magicclass-{id(gui)}"
    palette = get_palette(name, alignment=alignment)

    processed: set[int] = set()
    for parent, wdt in _iter_executable(gui):
        _id = id(wdt)
        if _id in processed:
            continue
        _qualname = type(parent).__qualname__
        palette.register(
            _define_command(wdt.changed.emit),
            title=_qualname,
            desc=wdt.text,
            when=_define_when(wdt, parent),
        )
        processed.add(_id)
    palette.sort(rule=lambda cmd: str(cmd.title.count(".")) + cmd.title + cmd.desc)
    _PALETTES[_id] = palette
    palette.install(gui.native)
    return palette.show_widget(gui.native)


def _define_command(fn: Callable) -> Callable:
    return lambda: fn()


def _define_when(wdt: Clickable, parent: BaseGui) -> Callable[[], bool]:
    return lambda: wdt.enabled


def _iter_executable(gui: BaseGui) -> Iterable[tuple[BaseGui, Clickable]]:
    for child in gui.__magicclass_children__:
        yield from _iter_executable(child)
    for wdt in gui:
        if is_clickable(wdt):
            if wdt._unwrapped:  # @wraps
                continue
            yield gui, wdt
        elif isinstance(wdt, BaseGui):
            yield from _iter_executable(wdt)
