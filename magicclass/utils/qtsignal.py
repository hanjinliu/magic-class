from qtpy.QtCore import Signal, QObject
from typing import Callable, Any


class QtSignal(QObject):
    """Dummy qt object for pyqt signal operations."""

    signal = Signal(object)

    def connect(self, slot: Callable):
        return self.signal.connect(slot)

    def emit(self, val: Any = None):
        return self.signal.emit(val)
