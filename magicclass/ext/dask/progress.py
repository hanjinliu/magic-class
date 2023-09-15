from __future__ import annotations

from functools import wraps
import inspect
from typing import Any, Callable, TYPE_CHECKING
from dask.diagnostics import Callback as DaskCallback
from psygnal import Signal
from superqt.utils import FunctionWorker, GeneratorWorker, create_worker

from magicclass.utils import move_to_screen_center, QtSignal
from magicclass.utils.qthreading import (
    CallbackList,
    DefaultProgressBar,
    thread_worker,
    ProgressDict,
)

if TYPE_CHECKING:
    from magicclass._gui import BaseGui


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
        self._worker: FunctionWorker | GeneratorWorker | None = None
        self._dt = dt
        self._state = None
        self._running = False
        self._frac = 0.0
        self._n_computation = 0
        super().__init__(max=max)
        self._computed_signal = QtSignal()
        self._computed_signal.connect(self._on_computed)
        self._new_cycle_signal = QtSignal()

    def __enter__(self):
        self._n_computation = 0
        self._on_timer_updated()
        return super().__enter__()

    def _start(self, dsk):
        self._state = None
        self._frac = 0.0
        self._new_cycle_signal.emit(self._n_computation)
        self._n_computation += 1
        self._timer.reset()
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
            else:
                self._frac = 1.0
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

    def _finish(self, dsk=None, state=None, errored=None):
        self._frac = 1.0
        self._running = False
        self._thread_timer.join()
        return None

    def set_worker(self, worker: GeneratorWorker | FunctionWorker):
        """Set currently running worker."""
        self._worker = worker
        if not isinstance(self._worker, GeneratorWorker):
            # FunctionWorker does not have yielded/aborted signals.
            self.hide_footer()
            return None
        # initialize abort_button
        self.abort_button.text = "Abort"
        self.abort_button.changed.connect(self._abort_worker)
        self.abort_button.enabled = True

        # initialize pause_button
        self.pause_button.text = "Pause"
        self.pause_button.enabled = True
        self.pause_button.changed.connect(self._toggle_pause)

        @self._worker.paused.connect
        def _on_pause():
            self.pause_button.text = "Resume"
            self.pause_button.enabled = True
            self._timer.stop()

        return None

    def increment(self, yielded=None):
        # Dask progressbar is incremented by computed signal.
        # Do not increment by yielded signal.
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
        self._callback_dict_["computed"] = CallbackList()

    @property
    def computed(self) -> CallbackList[Any]:
        return self._callback_dict_["computed"]

    def _create_method(self, gui: BaseGui):
        if self._progress is not None:
            self._progress["pbar"] = None

        return super()._create_method(gui)

    def _create_qt_worker(
        self, gui, *args, **kwargs
    ) -> FunctionWorker | GeneratorWorker:
        gui_id = id(gui)
        if self._progress:
            pbar = self._DEFAULT_PROGRESS_BAR(max=self._DEFAULT_TOTAL)
            self._progressbars[gui_id] = pbar
            for c in self.computed._iter_as_method(gui):
                pbar.computed.connect(c)
            if descs := self._progress.get("descs"):
                if callable(descs):
                    arguments = self.__signature__.bind(gui, *args, **kwargs)
                    arguments.apply_defaults()
                    _descs = lambda: descs(**_filter_args(descs, arguments.arguments))
                else:
                    _descs = lambda: iter(descs)
                self._progress["desc"] = next(_descs(), "<No description>")
                it = _descs()

                @pbar._new_cycle_signal.connect
                def _(i: int):
                    pbar.set_description(next(it, "<No description>"))

            pbar.native.setParent(gui.native, self.__class__._WINDOW_FLAG)
            move_to_screen_center(pbar.native)
            if self.is_generator:

                @self.yielded.connect
                def _(*args):
                    pbar.value = 0

            worker = create_worker(
                self._define_function(pbar, gui).__get__(gui),
                _ignore_errors=self._ignore_errors,
                _start_thread=False,
                *args,
                **kwargs,
            )
        else:
            worker = super()._create_qt_worker(gui, *args, **kwargs)
        return worker

    def _define_function(self, pbar, gui: BaseGui):
        if inspect.isgeneratorfunction(self._func):

            @wraps(self._func)
            def _wrapped(*args, **kwargs):
                with pbar:
                    with self._call_context(gui):
                        out = yield from self._func(*args, **kwargs)
                return out

        else:

            @wraps(self._func)
            def _wrapped(*args, **kwargs):
                with pbar:
                    with self._call_context(gui):
                        out = self._func(*args, **kwargs)
                return out

        return _wrapped


def _filter_args(fn: Callable, arguments: dict[str, Any]) -> dict[str, Any]:
    sig = inspect.signature(fn)
    params = sig.parameters
    nparams = len(params)
    if nparams == 0:
        return {}
    if list(sig.parameters.values())[-1] == inspect.Parameter.VAR_KEYWORD:
        return arguments
    existing_args = set(sig.parameters.keys())
    return {k: v for k, v in arguments.items() if k in existing_args}
