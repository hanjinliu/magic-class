# Built-in command palette for magicclass
# Currently it is not very customizable.

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable
from typing_extensions import Literal
from qt_command_palette import get_palette
from magicgui.widgets import Widget
from magicclass._gui import BaseGui
from magicclass._gui.mgui_ext import Clickable, is_clickable

if TYPE_CHECKING:
    from qt_command_palette._api import CommandPalette

_PALETTES: dict[int, CommandPalette] = {}


def exec_command_palette(
    gui: BaseGui,
    alignment: Literal["parent", "screen"] = "parent",
    title: Callable[[Widget, Clickable], str] | None = None,
    desc: Callable[[Widget, Clickable], str] | None = None,
    filter: Callable[[Widget, Clickable], str] | None = None,
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
    title : callable, optional
        Formatter function for the title of each command. The function should
        take two arguments. For a command corresponding to a button, the first
        argument is the parent magic-class instance, and the second argument
        is the button widget itself.
    desc : callable, optional
        Formatter function for the description of each command. The function
        takes the same arguments as `title`.
    filter : callable, optional
        Filter function for the commands. The function should take the same
        arguments as `title`. If the function returns False, the command will
        not be registered.
    """
    _id = id(gui)
    if _id in _PALETTES:
        return _PALETTES[_id].show_widget(gui.native)
    name = f"magicclass-{id(gui)}"
    palette = get_palette(name, alignment=alignment)

    if title is None:
        title = lambda mcls, btn: type(mcls).__qualname__
    if desc is None:
        desc = lambda mcls, btn: btn.text
    if filter is None:
        filter = lambda mcls, btn: True

    processed: set[int] = set()
    for parent, wdt in _iter_executable(gui):
        _id = id(wdt)
        if _id in processed:
            continue
        if not filter(parent, wdt):
            continue
        palette.register(
            _define_command(wdt.changed.emit),
            title=title(parent, wdt),
            desc=desc(parent, wdt),
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
