from __future__ import annotations
from contextlib import contextmanager
from typing import TYPE_CHECKING
import weakref
from macrokit import Macro
from psygnal import SignalInstance
from .mgui_ext import PushButtonPlus, ToolButtonPlus, Action

if TYPE_CHECKING:
    from ._base import BaseGui, ContainerLikeGui
    from magicgui.widgets import Container


class MacroCoder:
    CODING = False

    def __init__(self, gui: BaseGui):
        self._parent_ref = weakref.ref(gui)
        self._macro_instance = Macro(flags={"Get": False, "Return": False})

    @property
    def parent(self) -> BaseGui:
        return self._parent_ref()

    @property
    def macro(self) -> Macro:
        return self._macro_instance

    def set_coding(self) -> None:
        if self.__class__.CODING == True:
            return None
        self.__class__.CODING = True
        parent = self.parent
        parent.macro.callbacks.append(self._send)
        _block_signals(parent)
        return None

    @contextmanager
    def coding(self):
        self.set_coding()
        try:
            yield
        finally:
            self.reset()

    def reset(self):
        if self.__class__.CODING == False:
            return None
        parent = self.parent
        parent.macro.callbacks.remove(self._send)
        _unblock_signals(parent)
        self.__class__.CODING = False
        return None

    @contextmanager
    def resetting(self):
        self.reset()
        try:
            yield
        finally:
            self.set_coding()

    def execute(self):
        ui = self.parent
        with self.resetting():
            self._macro_instance.eval({}, {str(ui._my_symbol): ui})

    def _send(self, _=None):
        self._macro_instance.append(self.parent.macro.pop())


_DO_NOT_BLOCK = (PushButtonPlus, ToolButtonPlus, Action)


def _block_signals(gui: Container | ContainerLikeGui):
    for wdt in gui:
        if not isinstance(getattr(wdt, "changed", None), SignalInstance):
            continue
        ins: SignalInstance = wdt.changed
        if not isinstance(wdt, _DO_NOT_BLOCK):
            ins.block()
        if hasattr(wdt, "__iter__"):
            _block_signals(wdt)


def _unblock_signals(gui: Container | ContainerLikeGui):
    for wdt in gui:
        if not isinstance(getattr(wdt, "changed", None), SignalInstance):
            continue
        ins: SignalInstance = wdt.changed
        if not isinstance(wdt, _DO_NOT_BLOCK):
            ins.unblock()
        if hasattr(wdt, "__iter__"):
            _block_signals(wdt)
