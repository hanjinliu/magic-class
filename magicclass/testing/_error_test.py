from __future__ import annotations
from contextlib import contextmanager

from typing import TYPE_CHECKING, Iterator, Sequence

if TYPE_CHECKING:
    from magicclass._gui import BaseGui


class GuiErrorMonitor(Sequence[Exception]):
    _instances: dict[BaseGui, GuiErrorMonitor] = {}

    def __init__(self, gui: BaseGui):
        self._errors: list[Exception] = []

    @classmethod
    def get_instance(cls, gui: BaseGui) -> GuiErrorMonitor:
        if gui in cls._instances:
            return cls._instances[gui]
        return cls._instances.setdefault(gui, cls(gui))

    def __getitem__(self, index: int) -> Exception:
        return self._errors[index]

    def __len__(self) -> int:
        return len(self._errors)

    def __iter__(self) -> Iterator[Exception]:
        return iter(self._errors)

    @contextmanager
    def catch(self):
        try:
            yield
        except Exception as e:
            self._errors.append(e)
