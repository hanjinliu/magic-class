from __future__ import annotations
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
    Protocol,
    runtime_checkable,
)
from typing_extensions import TypedDict

try:
    from superqt.utils import create_worker, GeneratorWorker, FunctionWorker
except ImportError as e:  # pragma: no cover
    msg = f"{e}. To use magicclass with threading please `pip install superqt`"
    raise type(e)(msg)

from qtpy.QtCore import Qt
from magicgui.widgets import ProgressBar, Container, Widget, PushButton
from magicgui.application import use_app

from . import get_signature, move_to_screen_center

if TYPE_CHECKING:
    from ..gui import BaseGui
    from ..gui.mgui_ext import PushButtonPlus, Action

__all__ = ["thread_worker"]

_F = TypeVar("_F", bound=Callable)


class ProgressDict(TypedDict):
    """Supported keys for the progress argument."""

    desc: str | Callable
    total: str | Callable
    pbar: Any


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


class Callbacks:
    """List of callback functions."""

    def __init__(self):
        self._callbacks: list[Callable] = []

    @property
    def callbacks(self) -> tuple[Callable, ...]:
        return tuple(self._callbacks)

    def connect(self, callback: _F) -> _F:
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

    def disconnect(self, callback: _F) -> _F:
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


class DefaultProgressBar(Container, _SupportProgress):
    """The default progressbar widget."""

    def __init__(self, max: int = 1):
        self.pbar = ProgressBar(value=0, max=max)
        self.pause_button = PushButton(text="Pause")
        self.abort_button = PushButton(text="Abort")
        cnt = Container(
            layout="horizontal", widgets=[self.pause_button, self.abort_button]
        )
        cnt.margins = (0, 0, 0, 0)
        self.pbar.min_width = 200
        self._paused = False
        super().__init__(widgets=[self.pbar, cnt])

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
        self.pbar.label = desc
        self._unify_label_widths()
        return None

    def set_worker(self, worker: GeneratorWorker | FunctionWorker):
        """Set currently running worker."""
        self._worker = worker
        if not isinstance(self._worker, GeneratorWorker):
            # FunctionWorker does not have yielded/aborted signals.
            self.pause_button.enabled = False
            self.abort_button.enabled = False
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

        return None

    def _toggle_pause(self):
        if self._paused:
            self._worker.resume()
            self.pause_button.text = "Pause"
        else:
            self._worker.pause()
            self.pause_button.text = "Pausing"
            self.pause_button.enabled = False

        self._paused = not self._paused
        return None

    def _abort_worker(self):
        self._paused = False
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
        if not args:
            args = ("Function call is aborted.",)
        raise cls(*args)


ProgressBarLike = Union[ProgressBar, _SupportProgress]


class thread_worker:
    """Create a worker in a superqt/napari style."""

    _DEFAULT_PROGRESS_BAR = DefaultProgressBar

    def __init__(
        self,
        f: Callable | None = None,
        *,
        ignore_errors: bool = False,
        progress: ProgressDict | None = None,
    ) -> None:
        self._func: Callable | None = None
        self._started = Callbacks()
        self._returned = Callbacks()
        self._errored = Callbacks()
        self._yielded = Callbacks()
        self._finished = Callbacks()
        self._aborted = Callbacks()
        self._ignore_errors = ignore_errors
        self._objects: dict[int, BaseGui] = {}
        self._progressbars: dict[int, ProgressBarLike | None] = {}
        self._last_arguments = tuple(), dict()

        if f is not None:
            self(f)

        if progress:
            if isinstance(progress, bool):
                progress = {}

            desc = progress.get("desc", None)
            total = progress.get("total", 0)
            pbar = progress.get("pbar", None)

            progress = {"desc": desc, "total": total, "pbar": pbar}

        self._progress = progress

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

    @overload
    def __call__(self, f: Callable) -> thread_worker:
        ...

    @overload
    def __call__(self, bgui: BaseGui, *args, **kwargs) -> Any:
        ...

    def __call__(self, *args, **kwargs):
        if self._func is None:
            f = args[0]
            self._func = f
            wraps(f)(self)
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

    def _create_method(self, gui: BaseGui):
        from ..fields import MagicField

        @wraps(self)
        def _create_worker(*args, **kwargs):
            # create a worker object
            worker: FunctionWorker | GeneratorWorker = create_worker(
                self._func.__get__(gui),
                _ignore_errors=self._ignore_errors,
                _start_thread=False,
                *args,
                **kwargs,
            )
            self._last_arguments = args, kwargs

            if self._progress:
                _desc = self._progress["desc"]
                _total = self._progress["total"]

                if callable(_desc):
                    desc = _desc(gui)
                else:
                    desc = str(_desc or self._func.__name__)

                if isinstance(_total, str):
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

                # create progressbar widget (or any proper widget)
                _pbar = self._progress["pbar"]
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

                worker.started.connect(init_pbar.__get__(pbar))

            for c in self._started._iter_as_method(gui):
                worker.started.connect(c)
            for c in self._returned._iter_as_method(gui):
                worker.returned.connect(c)
            for c in self._errored._iter_as_method(gui):
                worker.errored.connect(c)
            for c in self._finished._iter_as_method(gui):
                worker.finished.connect(c)

            if isinstance(worker, GeneratorWorker):
                for c in self._aborted._iter_as_method(gui):
                    worker.aborted.connect(c)
                for c in self._yielded._iter_as_method(gui):
                    worker.yielded.connect(c)

            if self._progress:
                if not getattr(pbar, "visible", False):
                    # return the progressbar to the initial state
                    worker.finished.connect(close_pbar.__get__(pbar))
                if pbar.max != 0 and isinstance(worker, GeneratorWorker):
                    worker.pbar = pbar  # avoid garbage collection
                    worker.yielded.connect(increment.__get__(pbar))

                if hasattr(pbar, "set_worker"):
                    # if _SupportProgress object support set_worker
                    pbar.set_worker(worker)

            _obj: PushButtonPlus | Action = gui[self._func.__name__]
            if _obj.running:
                _obj.enabled = False
                worker.finished.connect(lambda: setattr(_obj, "enabled", True))
                worker.errored.connect(
                    partial(gui._error_mode.get_handler(), parent=gui)
                )
                if isinstance(worker, GeneratorWorker):
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
                _pbar.native.setParent(
                    gui.native,
                    Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.Window,
                )
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
    def started(self) -> Callbacks:
        """Event that will be emitted on started."""
        return self._started

    @property
    def returned(self) -> Callbacks:
        """Event that will be emitted on returned."""
        return self._returned

    @property
    def errored(self) -> Callbacks:
        """Event that will be emitted on errored."""
        return self._errored

    @property
    def yielded(self) -> Callbacks:
        """Event that will be emitted on yielded."""
        if not self.is_generator:
            raise TypeError(
                f"Worker of non-generator function {self._func!r} does not have "
                "yielded signal."
            )
        return self._yielded

    @property
    def finished(self) -> Callbacks:
        """Event that will be emitted on finished."""
        return self._finished

    @property
    def aborted(self) -> Callbacks:
        """Event that will be emitted on aborted."""
        if not self.is_generator:
            raise TypeError(
                f"Worker of non-generator function {self._func!r} does not have "
                "aborted signal."
            )
        return self._aborted


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
