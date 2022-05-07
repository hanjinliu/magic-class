from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING
from dask.diagnostics import Callback as DaskCallback
from psygnal import Signal
from superqt.utils import FunctionWorker, GeneratorWorker, create_worker

from ...utils import move_to_screen_center, QtSignal
from ...utils.qthreading import (
    Callbacks,
    DefaultProgressBar,
    thread_worker,
    ProgressDict,
)

if TYPE_CHECKING:
    from ..._gui import BaseGui


class DaskProgressBar(DefaultProgressBar, DaskCallback):
    """A progress bar widget for dask computation."""

    computed = Signal(object)

    def __init__(
        self,
        max: int = 100,
        minimum: float = 0.5,
        dt: float = 0.1,
    ):
        self._minimum = minimum
        self._dt = dt
        self._frac = 0.0
        self._n_computation = 0
        super().__init__(max=max)
        self.footer[1].visible = self.footer[2].visible = False
        self._computed_signal = QtSignal()
        self._computed_signal.connect(self._on_computed)

    def __enter__(self):
        self._n_computation = 0
        self._on_timer_updated()
        return super().__enter__()

    def _start(self, dsk):
        self._state = None
        self._frac = 0.0
        self._n_computation += 1
        self._start_thread()
        return None

    def _on_computed(self, result):
        s = self._state
        if not s:
            self._frac = 0.0
        else:
            ndone = len(s["finished"])
            ntasks = sum(len(s[k]) for k in ["ready", "waiting", "running"]) + ndone
            if ndone <= ntasks:
                self._frac = ndone / ntasks if ntasks else 0.0
        self.pbar.value = self.max * self._frac
        self.computed.emit(result)
        return None

    def _pretask(self, key, dsk, state):
        self._state = state
        return None

    def _posttask(self, key, result, dsk, state, worker_id):
        self._computed_signal.emit(result)
        self._time_signal.emit()
        return None

    def _finish(self, dsk, state, errored):
        self._frac = 1.0
        self._running = False
        self._thread_timer.join()
        self._timer.reset()
        return None

    def _on_timer_updated(self, _=None):
        if self._n_computation > 1:
            _prefix = f"({self._n_computation}) "
        else:
            _prefix = ""
        if self._timer.sec < 3600:
            self.time_label.value = _prefix + self._timer.format_time(
                "{min:0>2}:{sec:0>2}"
            )
        else:
            self.time_label.value = _prefix + self._timer.format_time()
        return None

    def set_worker(self, worker: GeneratorWorker | FunctionWorker):
        """Set currently running worker."""
        self._worker = worker
        if isinstance(self._worker, GeneratorWorker):
            raise TypeError("Cannot set generator.")
        self.footer[1].visible = False
        self.footer[2].visible = False
        self._time_signal.emit()
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

    _DEFAULT_PROGRESS_BAR = DaskProgressBar
    _DEFAULT_TOTAL = 100

    def __init__(
        self,
        f: Callable | None = None,
        *,
        ignore_errors: bool = False,
        progress: ProgressDict | bool | None = True,
    ) -> None:
        super().__init__(f, ignore_errors=ignore_errors, progress=progress)
        self._callback_dict_["computed"] = Callbacks()

    @property
    def computed(self) -> Callbacks[Any]:
        return self._callback_dict_["computed"]

    def _create_method(self, gui: BaseGui):
        if self._progress is None:
            self._progress = {
                "pbar": None,
                "desc": "Progress",
                "total": 100,
            }
        else:
            self._progress["pbar"] = None

        return super()._create_method(gui)

    def _create_qt_worker(
        self, gui, *args, **kwargs
    ) -> FunctionWorker | GeneratorWorker:
        gui_id = id(gui)
        if gui_id in self._progressbars:
            pbar = self._progressbars[gui_id]
        else:
            pbar = self._DEFAULT_PROGRESS_BAR(max=self._DEFAULT_TOTAL)
            self._progressbars[gui_id] = pbar
            for c in self.computed._iter_as_method(gui):
                pbar.computed.connect(c)
            pbar.native.setParent(gui.native, self.__class__._WINDOW_FLAG)
            move_to_screen_center(pbar.native)

        worker = create_worker(
            self._define_function(pbar).__get__(gui),
            _ignore_errors=self._ignore_errors,
            _start_thread=False,
            *args,
            **kwargs,
        )

        return worker

    def _define_function(self, pbar):
        @wraps(self._func)
        def _wrapped(*args, **kwargs):
            with pbar:
                out = self._func(*args, **kwargs)
            return out

        return _wrapped
