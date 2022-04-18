from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING
import time
from dask.diagnostics import Callback as DaskCallback
from psygnal import Signal
from qtpy import QtCore
from qtpy.QtWidgets import QWidget
from superqt.utils import FunctionWorker, GeneratorWorker

from ...utils import move_to_screen_center
from ...utils.qthreading import (
    Callbacks,
    DefaultProgressBar,
    thread_worker,
    ProgressDict,
)

if TYPE_CHECKING:
    from ..._gui import BaseGui


class Dummy(QWidget):
    """Dummy widget for pyqt signal operations."""

    computed = QtCore.Signal(object)


class DaskProgressBar(DefaultProgressBar, DaskCallback):
    computed = Signal(object)

    def __init__(
        self,
        max: int = 100,
        minimum: float = 0.5,
        dt: float = 0.1,
    ):
        self._minimum = minimum
        self._dt = dt
        self.last_duration = 0
        super().__init__(max=max)
        self._dummy = Dummy()

        self._dummy.computed.connect(self._on_computed)

    def _start(self, dsk):
        self._state = None
        self._start_thread()

    def _on_computed(self, result):
        self.pbar.value = self.max * self._frac
        self.computed.emit(result)

    def _pretask(self, key, dsk, state):
        self._state = state

    def _posttask(self, key, result, dsk, state, worker_id):
        self._dummy.computed.emit(result)

    def _finish(self, dsk, state, errored):
        self._running = False
        self._thread_timer.join()
        elapsed = self._timer.sec
        self.last_duration = elapsed
        self._frac = 1.0
        self._timer.reset()
        if elapsed < self._minimum:
            return

    def _update_timer_label(self):
        """Background thread for updating the progress bar"""
        while self._running:
            elapsed = self._timer.sec
            if elapsed > self._minimum:
                self._update_bar(elapsed)

            if self._timer._running:
                if self._timer.sec < 3600:
                    self.time_label.value = self._timer.format_time(
                        "{min:0>2}:{sec:0>2}"
                    )
                else:
                    self.time_label.value = self._timer.format_time()

            time.sleep(0.1)

    def _update_bar(self, elapsed):
        s = self._state
        if not s:
            self._frac = 0
            return
        ndone = len(s["finished"])
        ntasks = sum(len(s[k]) for k in ["ready", "waiting", "running"]) + ndone
        if ndone < ntasks:
            self._frac = ndone / ntasks if ntasks else 0

    @property
    def value(self) -> int:
        return self.pbar.value

    @value.setter
    def value(self, v):
        self.pbar.value = v

    def set_worker(self, worker: GeneratorWorker | FunctionWorker):
        """Set currently running worker."""
        self._worker = worker
        if isinstance(self._worker, GeneratorWorker):
            raise TypeError("Cannot set generator.")
        self.footer[1].visible = False
        self.footer[2].visible = False
        return None


class dask_thread_worker(thread_worker):
    """
    Create a dask's worker in a superqt/napari style.

    This thread worker class can monitor the progress of dask computation.
    Callback function connected to ``computed`` signal will get called when any one
    of the tasks are finished. The returned value of the task will be sent to the
    callback argument. The returned value is useful if delayed functions are computed
    but it is not always meaningful when dask mapping functions such as ``map_blocks``
    is used. Unlike standard ``thread_worker``, you should not specify ``total``
    parameter since dask progress bar knows it.

    Examples
    --------

    .. code-block:: python

        @magicclass
        class A:
            @dask_thread_worker
            def func(self):
                arr = da.random.random((30000, 30000))
                da.mean(arr).compute()

            @func.computed.connect
            def _on_computed(self, _=None):
                print("computed")

    """

    _DEFAULT_TOTAL = 100

    def __init__(
        self,
        f: Callable | None = None,
        *,
        ignore_errors: bool = False,
        progress: ProgressDict | bool | None = True,
    ) -> None:
        self._pbar_widget = None
        super().__init__(f, ignore_errors=ignore_errors, progress=progress)
        self._callback_dict_["computed"] = Callbacks()

    @property
    def computed(self) -> Callbacks[Any]:
        return self._callback_dict_["computed"]

    def _create_method(self, gui: BaseGui):
        if self._progress is None:
            self._progress = {
                "pbar": self.pbar_widget,
                "desc": "Progress",
                "total": 100,
            }
        else:
            self._progress["pbar"] = self.pbar_widget

        return super()._create_method(gui)

    def __call__(self, *args, **kwargs):
        if self._func is None:
            f = args[0]

            @wraps(f)
            def _wrapped(*args, **kwargs):
                with self.pbar_widget:
                    out = f(*args, **kwargs)
                return out

            self._func = _wrapped
            wraps(f)(self)  # NOTE: __name__ etc. are updated here.
            return self
        else:
            return self._func(*args, **kwargs)

    def _find_progressbar(self, gui: BaseGui, desc: str | None = None, total: int = 0):
        """Find available progressbar. Create a new one if not found."""
        if desc is None:
            desc = "Progress"
        pbar = self.pbar_widget
        pbar.max = total
        pbar.native.setParent(gui.native, self.__class__._WINDOW_FLAG)
        move_to_screen_center(pbar.native)
        pbar.set_description(desc)
        return pbar

    def _bind_callbacks(self, worker: FunctionWorker | GeneratorWorker, gui):
        for c in self.computed._iter_as_method(gui):
            self.pbar_widget.computed.connect(c)
        return super()._bind_callbacks(worker, gui)

    @property
    def pbar_widget(self) -> DaskProgressBar:
        if self._pbar_widget is None:
            self._pbar_widget = DaskProgressBar()
        return self._pbar_widget
