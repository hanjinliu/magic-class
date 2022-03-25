from __future__ import annotations
import inspect
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING, Iterable, Union, overload, TypeVar

try:
    from superqt.utils import create_worker, GeneratorWorker, FunctionWorker
except ImportError as e:  # pragma: no cover
    msg = f"{e}. To use magicclass with threading please `pip install superqt`"
    raise type(e)(msg)

from magicgui.widgets import ProgressBar

from .fields import MagicField
from .utils.functions import get_signature

if TYPE_CHECKING:
    from .gui import BaseGui
    from .gui.mgui_ext import PushButtonPlus

__all__ = ["thread_worker"]

_F = TypeVar("_F", bound=Callable)


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
        for callback in self._callbacks:

            def f(*args, **kwargs):
                with obj.macro.blocked():
                    out = callback.__get__(obj)(*args, **kwargs)
                return out

            yield f


class NapariProgressBar:
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

    @property
    def label(self) -> str:
        return self._pbar.desc

    @label.setter
    def label(self, v) -> None:
        self._pbar.set_description(v)

    @property
    def visible(self) -> bool:
        return False

    def show(self):
        type(self._pbar)._all_instances.events.changed(added={self._pbar}, removed={})

    def close(self):
        self._pbar.close()


_SupportProgress = Union[ProgressBar, NapariProgressBar]


class thread_worker:
    """Create a worker in a superqt/napari style."""

    def __init__(
        self,
        f: Callable | None = None,
        *,
        ignore_errors: bool = False,
        progress: dict[str, Any] | None = None,
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
        self._progressbars: dict[int, _SupportProgress | None] = {}

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

    @property
    def not_ready(self) -> bool:
        return self._func is None

    @overload
    def __call__(self, f: Callable) -> thread_worker:
        ...

    @overload
    def __call__(self, bgui: BaseGui, *args, **kwargs) -> Any:
        ...

    def __call__(self, *args, **kwargs):
        if self.not_ready:
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

        @wraps(self)
        def _create_worker(*args, **kwargs):
            worker: FunctionWorker | GeneratorWorker = create_worker(
                self._func.__get__(gui),
                _ignore_errors=self._ignore_errors,
                *args,
                **kwargs,
            )
            for c in self._started._iter_as_method(gui):
                worker.started.connect(c)
            for c in self._returned._iter_as_method(gui):
                worker.returned.connect(c)
            for c in self._errored._iter_as_method(gui):
                worker.errored.connect(c)
            for c in self._yielded._iter_as_method(gui):
                worker.yielded.connect(c)
            for c in self._finished._iter_as_method(gui):
                worker.finished.connect(c)
            for c in self._aborted._iter_as_method(gui):
                worker.aborted.connect(c)

            if self._progress:
                _desc = self._progress["desc"]
                _total = self._progress["total"]

                if callable(_desc):
                    desc = _desc(gui)
                else:
                    desc = str(_desc)

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
                    if not isinstance(_pbar, ProgressBar):
                        raise TypeError(f"{_pbar} is not a ProgressBar.")
                    pbar = _pbar

                worker.started.connect(init_pbar.__get__(pbar))
                if not pbar.visible:
                    worker.finished.connect(close_pbar.__get__(pbar))
                if pbar.max != 0 and isinstance(worker, GeneratorWorker):
                    worker.pbar = pbar  # avoid garbage collection
                    worker.yielded.connect(increment.__get__(pbar))

            _push_button: PushButtonPlus = gui[self._func.__name__]
            if _push_button.running:
                _push_button.enabled = False

                @worker.finished.connect
                def _enable():
                    _push_button.enabled = True

                worker.start()
            else:
                worker.run()
            return None

        _create_worker.__signature__ = self._get_method_signature()

        self._objects[gui_id] = _create_worker  # cache
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
            if gui.parent_viewer is not None:
                _pbar = NapariProgressBar(value=0, max=total)
            else:
                _pbar = ProgressBar(value=0, max=total)
                _pbar.native.setParent(gui.native, _pbar.native.windowFlags())
        else:
            _pbar.max = total

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
        return self._yielded

    @property
    def finished(self) -> Callbacks:
        """Event that will be emitted on finished."""
        return self._finished

    @property
    def aborted(self) -> Callbacks:
        """Event that will be emitted on aborted."""
        return self._aborted


def init_pbar(pbar: _SupportProgress):
    """Initialize progressbar."""
    pbar.value = 0
    pbar.show()
    return None


def close_pbar(pbar: _SupportProgress):
    """Close progressbar."""
    if isinstance(pbar, ProgressBar):
        _labeled_widget = pbar._labeled_widget()
        if _labeled_widget is not None:
            pbar = _labeled_widget
    pbar.close()
    return None


def increment(pbar: _SupportProgress):
    """Increment progressbar."""
    if pbar.value == pbar.max:
        pbar.max = 0
    else:
        pbar.value += 1
    return None
