from __future__ import annotations
from functools import wraps
from typing import Callable
import time
from timeit import default_timer
import threading
from dask.diagnostics import Callback as DaskCallback
from superqt.utils import FunctionWorker, GeneratorWorker
from ...utils.qthreading import (
    DefaultProgressBar,
    thread_worker,
    ProgressDict,
    Callbacks,
)


class DaskProgressBar(DefaultProgressBar, DaskCallback):
    def __init__(
        self,
        max: int = 100,
        minimum: int = 0,
        dt: float = 0.1,
    ):
        self._minimum = minimum
        self._dt = dt
        self.last_duration = 0
        self._callbacks: list[Callable] = []
        super().__init__(max=max)

    def _start(self, dsk):
        self._state = None
        self._start_time = default_timer()
        # Start background thread
        self._running = True
        self._thread_timer = threading.Thread(target=self._timer_func)
        self._thread_timer.daemon = True
        self._thread_timer.start()

    def _pretask(self, key, dsk, state):
        self._state = state

    def _finish(self, dsk, state, errored):
        self._running = False
        self._thread_timer.join()
        elapsed = default_timer() - self._start_time
        self.last_duration = elapsed
        if elapsed < self._minimum:
            return
        if not errored:
            self._draw_bar(1, elapsed)
        else:
            self._update_bar(elapsed)

    def _timer_func(self):
        """Background thread for updating the progress bar"""
        while self._running:
            elapsed = default_timer() - self._start_time
            if elapsed > self._minimum:
                self._update_bar(elapsed)
            time.sleep(self._dt)

    def _update_bar(self, elapsed):
        s = self._state
        if not s:
            self._draw_bar(0, elapsed)
            return
        ndone = len(s["finished"])
        ntasks = sum(len(s[k]) for k in ["ready", "waiting", "running"]) + ndone
        if ndone < ntasks:
            self._draw_bar(ndone / ntasks if ntasks else 0, elapsed)

    def _draw_bar(self, frac, elapsed):
        self.value = self.max * frac
        min_all, sec = divmod(elapsed, 60)
        hour, min = divmod(min_all, 60)
        sec = int(sec)
        min = int(min)
        hour = int(hour)
        if elapsed < 3600:
            self.time_label.value = f"{min:0>2}:{sec:0>2}"
        else:
            self.time_label.value = f"{hour:0>2}:{min:0>2}:{sec:0>2}"

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


_DASK_PROGRESS_BAR = DaskProgressBar()


class dask_thread_worker(thread_worker):

    _DEFAULT_TOTAL = 100

    def __init__(
        self,
        f: Callable | None = None,
        *,
        ignore_errors: bool = False,
        progress: ProgressDict | bool | None = True,
    ) -> None:
        super().__init__(f, ignore_errors=ignore_errors, progress=progress)
        if self._progress is None:
            self._progress = {
                "pbar": _DASK_PROGRESS_BAR,
                "desc": "Progress",
                "total": 100,
            }
        else:
            self._progress["pbar"] = _DASK_PROGRESS_BAR

    def __call__(self, *args, **kwargs):
        if self._func is None:
            f = args[0]

            @wraps(f)
            def _wrapped(*args, **kwargs):
                with _DASK_PROGRESS_BAR:
                    out = f(*args, **kwargs)
                return out

            self._func = _wrapped
            wraps(f)(self)  # NOTE: __name__ etc. are updated here.
            return self
        else:
            return self._func(*args, **kwargs)
