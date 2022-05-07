from qtpy import QtCore
from typing import Callable, Any


class QtSignal(QtCore.QObject):
    """Dummy qt object for pyqt signal operations."""

    signal = QtCore.Signal(object)

    def connect(self, slot: Callable):
        return self.signal.connect(slot)

    def emit(self, val: Any = None):
        return self.signal.emit(val)
