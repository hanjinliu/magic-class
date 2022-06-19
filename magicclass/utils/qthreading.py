from __future__ import annotations
import threading
import time
from timeit import default_timer
import inspect
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
    Iterable,
    Union,
    overload,
    TypeVar,
    Generic,
    Protocol,
    runtime_checkable,
)
from typing_extensions import TypedDict, ParamSpec

from superqt.utils import create_worker, GeneratorWorker, FunctionWorker
from qtpy.QtCore import Qt
from magicgui.widgets import ProgressBar, Container, Widget, PushButton, Label
from magicgui.application import use_app

from . import get_signature, move_to_screen_center
from .qtsignal import QtSignal

if TYPE_CHECKING:
    from .._gui import BaseGui
    from .._gui.mgui_ext import PushButtonPlus, Action
    from ..fields import MagicField

__all__ = ["thread_worker", "Timer"]


class ProgressDict(TypedDict):
    """Supported keys for the progress argument."""

    desc: str | Callable
    total: str | Callable
    pbar: ProgressBar | _SupportProgress | MagicField


@runtime_checkable
class _SupportProgress(Protocol):
    """
    A progress protocol.

    Progressbar must be implemented with methods ``__init__``, ``set_description``,
    ``show``, ``close`` and properties ``value``, ``max``. Optionally ``set_worker``
    can be used so that progressbar has an access to the worker object.
    """

    def __init__(self, max: int = 1, **kwargs):
        raise NotImplementedError()

    @property
    def value(self) -> int:
        raise NotImplementedError()

    @value.setter
    def value(self, v) -> None:
        raise NotImplementedError()

    @property
    def max(self) -> int:
        raise NotImplementedError()

    @max.setter
    def max(self, v) -> None:
        raise NotImplementedError()

    def set_description(self, desc: str):
        raise NotImplementedError()

    def show(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()


_P = ParamSpec("_P")
_R1 = TypeVar("_R1")
_R2 = TypeVar("_R2")


class Callbacks(Generic[_R1]):
    """List of callback functions."""

    def __init__(self):
        self._callbacks: list[Callable[[Any, _R1], _R2] | Callable[[Any], _R2]] = []

    @property
    def callbacks(self) -> tuple[Callable[[Any, _R1], _R2] | Callable[[Any], _R2], ...]:
        return tuple(self._callbacks)

    def connect(
        self, callback: Callable[[Any, _R1], _R2] | Callable[[Any], _R2]
    ) -> Callable[[Any, _R1], _R2] | Callable[[Any], _R2]:
        """
        Append a callback function to the callback list.

        Parameters
        ----------
        callback : Callable
            Callback function.
        """
        if not callable(callback):
            raise TypeError("Can only connect callable object.")
        self._callbacks.append(callback)
        return callback

    def disconnect(
        self, callback: Callable[[Any, _R1], _R2] | Callable[[Any], _R2]
    ) -> Callable[[Any, _R1], _R2] | Callable[[Any], _R2]:
        """
        Remove callback function from the callback list.

        Parameters
        ----------
        callback : Callable
            Callback function to be removed.
        """
        self._callbacks.remove(callback)
        return callback

    def _iter_as_method(self, obj: BaseGui) -> Iterable[Callable]:
        for ref in self._callbacks:
            yield _make_method(ref, obj)


def _make_method(func, obj: BaseGui):
    def f(*args, **kwargs):
        with obj.macro.blocked():
            out = func.__get__(obj)(*args, **kwargs)
        return out

    return f


class NapariProgressBar(_SupportProgress):
    """A progressbar class that provides napari progress bar with same API."""

    def __init__(self, value: int = 0, max: int = 1000):
        from napari.utils import progress

        with progress._all_instances.events.changed.blocker():
            self._pbar = progress(total=max)
            self._pbar.n = value

    @property
    def value(self) -> int:
        return self._pbar.n

    @value.setter
    def value(self, v) -> None:
        self._pbar.n = v
        self._pbar.events.value(value=self._pbar.n)

    @property
    def max(self) -> int:
        return self._pbar.total

    @max.setter
    def max(self, v) -> None:
        self._pbar.total = v

    def set_description(self, v: str) -> None:
        self._pbar.set_description(v)

    @property
    def visible(self) -> bool:
        return False

    def show(self):
        type(self._pbar)._all_instances.events.changed(added={self._pbar}, removed={})

    def close(self):
        self._pbar.close()


class Timer:
    """A timer class with intuitive API."""

    def __init__(self):
        self.reset()

    def __repr__(self) -> str:
        """Return string in format hh:mm:ss"""
        return self.format_time()

    @property
    def sec(self) -> float:
        """Return current second."""
        self.lap()
        return self._t_total

    def start(self):
        """Start timer."""
        self._t0 = default_timer()
        self._running = True

    def stop(self) -> float:
        """Stop timer."""
        self.lap()
        self._running = False

    def lap(self) -> float:
        """Return lap time."""
        if self._running:
            now = default_timer()
            self._t_total += now - self._t0
            self._t0 = now
        return self._t_total

    def reset(self):
        """Reset timer."""
        self._t0 = default_timer()
        self._t_total = 0.0
        self._running = False
        return None

    def format_time(self, fmt: str = "{hour:0>2}:{min:0>2}:{sec:0>2}") -> str:
        """Format current time."""
        min_all, sec = divmod(self.sec, 60)
        hour, min = divmod(min_all, 60)
        return fmt.format(hour=int(hour), min=int(min), sec=int(sec))


class DefaultProgressBar(Container, _SupportProgress):
    """The default progressbar widget."""

    def __init__(self, max: int = 1):
        self.progress_label = Label(value="Progress")
        self.pbar = ProgressBar(value=0, max=max)
        self.time_label = Label(value="00:00")
        self.pause_button = PushButton(text="Pause")
        self.abort_button = PushButton(text="Abort")
        cnt = Container(
            layout="horizontal",
            widgets=[self.time_label, self.pause_button, self.abort_button],
            labels=False,
        )
        cnt.margins = (0, 0, 0, 0)
        self.footer = cnt
        self.pbar.min_width = 200
        self._timer = Timer()
        self._time_signal = QtSignal()
        self._time_signal.connect(self._on_timer_updated)

        super().__init__(widgets=[self.progress_label, self.pbar, cnt], labels=False)

    def _on_timer_updated(self, _=None):
        if self._timer.sec < 3600:
            self.time_label.value = self._timer.format_time("{min:0>2}:{sec:0>2}")
        else:
            self.time_label.value = self._timer.format_time()
        return None

    def _start_thread(self):
        # Start background thread
        self._running = True
        self._thread_timer = threading.Thread(target=self._update_timer_label)
        self._thread_timer.daemon = True
        self._thread_timer.start()
        self._timer.start()
        return None

    def _update_timer_label(self):
        """Background thread for updating the progress bar"""
        while self._running:
            if self._timer._running:
                self._time_signal.emit()

            time.sleep(0.1)
        return None

    def _finish(self):
        self._running = False
        self._thread_timer.join()
        return None

    @property
    def paused(self) -> bool:
        return not self._timer._running

    @property
    def value(self) -> int:
        return self.pbar.value

    @value.setter
    def value(self, v):
        self.pbar.value = v

    @property
    def max(self) -> int:
        return self.pbar.max

    @max.setter
    def max(self, v):
        self.pbar.max = v

    def set_description(self, desc: str):
        """Set description as the label of the progressbar."""
        self.progress_label.value = desc
        return None

    def set_worker(self, worker: GeneratorWorker | FunctionWorker):
        """Set currently running worker."""
        self._worker = worker
        self._worker.finished.connect(self._finish)
        self._worker.started.connect(self._start_thread)
        if not isinstance(self._worker, GeneratorWorker):
            # FunctionWorker does not have yielded/aborted signals.
            self.footer[1].visible = False
            self.footer[2].visible = False
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

    def _toggle_pause(self):
        if self.paused:
            self._worker.resume()
            self.pause_button.text = "Pause"
            self._timer.start()
        else:
            self._worker.pause()
            self.pause_button.text = "Pausing"
            self.pause_button.enabled = False

        return None

    def _abort_worker(self):
        self.pause_button.text = "Pause"
        self.abort_button.text = "Aborting"
        self.pause_button.enabled = False
        self.abort_button.enabled = False
        self._worker.quit()
        return None


class Aborted(RuntimeError):
    """Raised when worker is aborted."""

    @classmethod
    def raise_(cls, *args):
        """A function version of "raise"."""
        if not args:
            args = ("Aborted.",)
        raise cls(*args)


ProgressBarLike = Union[ProgressBar, _SupportProgress]


class thread_worker:
    """Create a worker in a superqt/napari style."""

    _DEFAULT_PROGRESS_BAR = DefaultProgressBar
    _DEFAULT_TOTAL = 0
    _WINDOW_FLAG = Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.Window

    def __init__(
        self,
        f: Callable[_P, _R1] | None = None,
        *,
        ignore_errors: bool = False,
        progress: ProgressDict | None = None,
    ) -> None:
        self._func: Callable[_P, _R1] | None = None
        self._callback_dict_ = {
            "started": Callbacks(),
            "returned": Callbacks(),
            "errored": Callbacks(),
            "yielded": Callbacks(),
            "finished": Callbacks(),
            "aborted": Callbacks(),
        }

        self._ignore_errors = ignore_errors
        self._objects: dict[int, BaseGui] = {}
        self._progressbars: dict[int, ProgressBarLike | None] = {}
        self._recorder: Callable[_P, Any] | None = None

        if f is not None:
            self(f)

        if progress:
            if isinstance(progress, bool):
                progress = {}

            progress.setdefault("desc", None)
            progress.setdefault("total", 0)
            progress.setdefault("pbar", None)

        self._progress = progress

    @property
    def func(self) -> Callable[_P, _R1]:
        return self._func

    @classmethod
    def set_default(cls, pbar_cls: Callable | str):
        """
        Set the default progressbar class.

        This class method is useful when there is an user-defined class that
        follows ``_SupportProgress`` protocol.

        Parameters
        ----------
        pbar_cls : callable or str
            The default class. In principle this parameter does not have to be a
            class. As long as ``pbar_cls(max=...)`` returns a ``_SupportProgress``
            object it works. Either "default" or "napari" is also accepted.

        """
        if isinstance(pbar_cls, str):
            if pbar_cls == "napari":
                pbar_cls = NapariProgressBar
            elif pbar_cls == "default":
                pbar_cls = DefaultProgressBar
            else:
                raise ValueError(
                    f"Unknown progress bar {pbar_cls!r}. Must be either 'default' or "
                    "'napari', or a proper type object."
                )
        cls._DEFAULT_PROGRESS_BAR = pbar_cls
        return pbar_cls

    @property
    def is_generator(self) -> bool:
        """True if bound function is a generator function."""
        return inspect.isgeneratorfunction(self._func)

    def _set_recorder(self, recorder: Callable[_P, Any]):
        """
        Set macro recorder function.
        Must accept ``recorder(bgui, *args, **kwargs)``.
        """
        self._recorder = recorder
        return None

    @overload
    def __call__(self, f: Callable[_P, _R1]) -> thread_worker:
        ...

    @overload
    def __call__(self, bgui: BaseGui, *args, **kwargs) -> Any:
        ...

    def __call__(self, *args, **kwargs):
        if self._func is None:
            f = args[0]
            self._func = f
            wraps(f)(self)  # NOTE: __name__ etc. are updated here.
            return self
        else:
            return self._func(*args, **kwargs)

    def __get__(self, gui: BaseGui, objtype=None):
        if gui is None:
            return self

        gui_id = id(gui)
        if gui_id in self._objects:
            return self._objects[gui_id]

        _create_worker = self._create_method(gui)
        _create_worker.__signature__ = self._get_method_signature()

        self._objects[gui_id] = _create_worker  # cache
        return _create_worker

    def _create_qt_worker(
        self, gui, *args, **kwargs
    ) -> FunctionWorker | GeneratorWorker:
        """Create a worker object."""
        worker = create_worker(
            self._func.__get__(gui),
            _ignore_errors=self._ignore_errors,
            _start_thread=False,
            *args,
            **kwargs,
        )
        return worker

    def _create_method(self, gui: BaseGui):
        from ..fields import MagicField

        @wraps(self)
        def _create_worker(*args, **kwargs):
            # create a worker object
            worker = self._create_qt_worker(gui, *args, **kwargs)
            is_generator = isinstance(worker, GeneratorWorker)

            if self._progress:
                _desc = self._progress["desc"]
                _total = self._progress["total"]
                _pbar = self._progress["pbar"]

                all_args = None
                if callable(_desc):
                    arguments = self.__signature__.bind(gui, *args, **kwargs)
                    arguments.apply_defaults()
                    all_args = arguments.arguments
                    desc = _desc(**all_args)
                else:
                    desc = str(_desc or self._func.__name__)

                if isinstance(_total, str):
                    if all_args is None:
                        arguments = self.__signature__.bind(gui, *args, **kwargs)
                        arguments.apply_defaults()
                        all_args = arguments.arguments
                    total = eval(_total, {}, all_args)
                elif callable(_total):
                    total = _total(gui)
                elif isinstance(_total, int):
                    total = _total
                else:
                    raise TypeError(
                        "'total' must be int, callable or evaluatable string."
                    )

                if not is_generator:
                    total = self._DEFAULT_TOTAL

                # create progressbar widget (or any proper widget)
                if _pbar is None:
                    pbar = self._find_progressbar(
                        gui,
                        desc=desc,
                        total=total,
                    )
                elif isinstance(_pbar, MagicField):
                    pbar = _pbar.get_widget(gui)
                    if not isinstance(pbar, ProgressBar):
                        raise TypeError(f"{_pbar.name} does not create a ProgressBar.")
                    pbar.label = desc or _pbar.name
                    pbar.max = total
                else:
                    pbar = _pbar
                    pbar.set_description(desc)

                worker.started.connect(init_pbar.__get__(pbar))

            self._bind_callbacks(worker, gui)

            # bind macro-recorder if exists
            if self._recorder is not None:
                worker.returned.connect(lambda _: self._recorder(gui, *args, **kwargs))

            if self._progress:
                if not getattr(pbar, "visible", False):
                    # return the progressbar to the initial state
                    worker.finished.connect(close_pbar.__get__(pbar))
                if pbar.max != 0 and is_generator:
                    worker.pbar = pbar  # avoid garbage collection
                    worker.yielded.connect(increment.__get__(pbar))

                if hasattr(pbar, "set_worker"):
                    # if _SupportProgress object support set_worker
                    pbar.set_worker(worker)

            _obj: PushButtonPlus | Action = gui[self._func.__name__]
            if _obj.running:
                worker.errored.connect(
                    partial(gui._error_mode.get_handler(), parent=gui)
                )
                if is_generator:
                    worker.aborted.connect(
                        gui._error_mode.wrap_handler(Aborted.raise_, parent=gui)
                    )

                worker.start()
            else:
                # If function is called from script, some events must get processed by
                # the application while keep script stopping at each line of code.
                app = use_app()
                worker.returned.connect(app.process_events)
                worker.started.connect(app.process_events)
                if isinstance(worker, GeneratorWorker):
                    worker.yielded.connect(app.process_events)
                worker.run()

            return None

        return _create_worker

    def _get_method_signature(self) -> inspect.Signature:
        sig = self.__signature__
        params = list(sig.parameters.values())[1:]
        return sig.replace(parameters=params)

    def _bind_callbacks(self, worker: FunctionWorker | GeneratorWorker, gui):
        # bind callbacks
        is_generator = isinstance(worker, GeneratorWorker)
        for c in self.started._iter_as_method(gui):
            worker.started.connect(c)
        for c in self.returned._iter_as_method(gui):
            worker.returned.connect(c)
        for c in self.errored._iter_as_method(gui):
            worker.errored.connect(c)
        for c in self.finished._iter_as_method(gui):
            worker.finished.connect(c)

        if is_generator:
            for c in self.aborted._iter_as_method(gui):
                worker.aborted.connect(c)
            for c in self.yielded._iter_as_method(gui):
                worker.yielded.connect(c)

    @property
    def __signature__(self) -> inspect.Signature:
        """Get the signature of the bound function."""
        return get_signature(self._func)

    @__signature__.setter
    def __signature__(self, sig: inspect.Signature) -> None:
        """Update signature of the bound function."""
        if not isinstance(sig, inspect.Signature):
            raise TypeError(f"Cannot set type {type(sig)}.")
        self._func.__signature__ = sig
        return None

    def _find_progressbar(self, gui: BaseGui, desc: str | None = None, total: int = 0):
        """Find available progressbar. Create a new one if not found."""
        from ..fields import MagicField

        gui_id = id(gui)
        if gui_id in self._progressbars:
            _pbar = self._progressbars[gui_id]
        else:
            for name, attr in gui.__class__.__dict__.items():
                if isinstance(attr, MagicField):
                    attr = attr.get_widget(gui)
                if isinstance(attr, ProgressBar):
                    _pbar = self._progressbars[gui_id] = attr
                    if desc is None:
                        desc = name
                    break
            else:
                _pbar = self._progressbars[gui_id] = None
                if desc is None:
                    desc = "Progress"

        if _pbar is None:
            _pbar = self.__class__._DEFAULT_PROGRESS_BAR(max=total)
            if isinstance(_pbar, Widget) and _pbar.parent is None:
                # Popup progressbar as a splashscreen if it is not a child widget.
                _pbar.native.setParent(gui.native, self.__class__._WINDOW_FLAG)
                move_to_screen_center(_pbar.native)
        else:
            _pbar.max = total

        # try to set description
        if hasattr(_pbar, "set_description"):
            _pbar.set_description(desc)
        else:
            _pbar.label = desc
        return _pbar

    @property
    def started(self) -> Callbacks[None]:
        """Event that will be emitted on started."""
        return self._callback_dict_["started"]

    @property
    def returned(self) -> Callbacks[_R1]:
        """Event that will be emitted on returned."""
        return self._callback_dict_["returned"]

    @property
    def errored(self) -> Callbacks[Exception]:
        """Event that will be emitted on errored."""
        return self._callback_dict_["errored"]

    @property
    def yielded(self) -> Callbacks[_R1]:
        """Event that will be emitted on yielded."""
        if not self.is_generator:
            raise TypeError(
                f"Worker of non-generator function {self._func!r} does not have "
                "yielded signal."
            )
        return self._callback_dict_["yielded"]

    @property
    def finished(self) -> Callbacks[None]:
        """Event that will be emitted on finished."""
        return self._callback_dict_["finished"]

    @property
    def aborted(self) -> Callbacks[None]:
        """Event that will be emitted on aborted."""
        if not self.is_generator:
            raise TypeError(
                f"Worker of non-generator function {self._func!r} does not have "
                "aborted signal."
            )
        return self._callback_dict_["aborted"]


def init_pbar(pbar: ProgressBarLike):
    """Initialize progressbar."""
    pbar.value = 0
    pbar.show()
    return None


def close_pbar(pbar: ProgressBarLike):
    """Close progressbar."""
    if isinstance(pbar, ProgressBar):
        _labeled_widget = pbar._labeled_widget()
        if _labeled_widget is not None:
            pbar = _labeled_widget
    pbar.close()
    return None


def increment(pbar: ProgressBarLike):
    """Increment progressbar."""
    if pbar.value == pbar.max:
        pbar.max = 0
    else:
        pbar.value += 1
    return None
