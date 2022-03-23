from __future__ import annotations
import inspect
from typing import Any, Callable, TYPE_CHECKING, Union, overload

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


class Callbacks:
    """List of callback functions."""

    def __init__(self):
        self._callbacks: list[Callable] = []

    @property
    def callbacks(self) -> tuple[Callable, ...]:
        return tuple(self._callbacks)

    def connect(self, callback: Callable):
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

    def disconnect(self, callback: Callable):
        """
        Remove callback function from the callback list.

        Parameters
        ----------
        callback : Callable
            Callback function to be removed.
        """
        self._callbacks.remove(callback)

    def iter_as_method(self, obj: BaseGui):
        for callback in self._callbacks:

            def f(*args, **kwargs):
                with obj.macro.blocked():
                    out = callback.__get__(obj)(*args, **kwargs)
                return out

            yield f


class NapariProgressBar:
    """A progressbar class that provides napari progress bar with same API."""

    def __init__(self, value=0, max=1000):
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
            if not callable(desc):
                _desc = lambda x: desc
            else:
                _desc = desc
            if not callable(total):
                _total = lambda x: total
            else:
                _total = total

            progress = {"desc": _desc, "total": _total, "pbar": pbar}

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
            self.__name__ = f.__name__
            self.__qualname__ = f.__qualname__
            self.__doc__ = f.__doc__
            self.__annotations__ = f.__annotations__
            return self
        else:
            return self._func(*args, **kwargs)

    def __get__(self, obj: BaseGui, objtype=None):
        if obj is None:
            return self._func

        obj_id = id(obj)
        if obj_id in self._objects:
            return self._objects[obj_id]

        def _create_worker(*args, **kwargs):
            worker: FunctionWorker | GeneratorWorker = create_worker(
                self._func.__get__(obj), *args, **kwargs
            )
            for c in self._started.iter_as_method(obj):
                worker.started.connect(c)
            for c in self._returned.iter_as_method(obj):
                worker.returned.connect(c)
            for c in self._errored.iter_as_method(obj):
                worker.errored.connect(c)
            for c in self._yielded.iter_as_method(obj):
                worker.yielded.connect(c)
            for c in self._finished.iter_as_method(obj):
                worker.finished.connect(c)
            for c in self._aborted.iter_as_method(obj):
                worker.aborted.connect(c)

            if self._progress:
                pbar: _SupportProgress = self._progress["pbar"]
                if pbar is None:
                    pbar = self._find_progressbar(
                        obj,
                        desc=self._progress["desc"](obj),
                        total=self._progress["total"](obj),
                    )

                worker.started.connect(init_pbar.__get__(pbar))
                worker.finished.connect(close_pbar.__get__(pbar))
                if pbar.max != 0 and isinstance(worker, GeneratorWorker):
                    worker.pbar = pbar  # avoid garbage collection
                    worker.yielded.connect(increment.__get__(pbar))

            _push_button: PushButtonPlus = obj[self._func.__name__]
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
        _create_worker.__name__ = self.__name__
        _create_worker.__qualname__ = self.__qualname__
        self._objects[obj_id] = _create_worker  # cache
        return _create_worker

    def _get_method_signature(self) -> inspect.Signature:
        sig = self.__signature__
        params = list(sig.parameters.values())[1:]
        return sig.replace(parameters=params)

    @property
    def __signature__(self) -> inspect.Signature:
        return get_signature(self._func)

    @__signature__.setter
    def __signature__(self, sig: inspect.Signature) -> None:
        if not isinstance(sig, inspect.Signature):
            raise TypeError(f"Cannot set type {type(sig)}.")
        self._func.__signature__ = sig

    def _find_progressbar(self, obj: BaseGui, desc: str | None = None, total: int = 0):
        obj_id = id(obj)
        if obj_id in self._progressbars:
            _pbar = self._progressbars[obj_id]

        gui_cls = obj.__class__
        for name, attr in gui_cls.__dict__.items():
            if isinstance(attr, MagicField):
                attr = attr.get_widget(obj)
            if isinstance(attr, ProgressBar):
                _pbar = self._progressbars[obj_id] = attr
                if desc is None:
                    desc = name
                break
        else:
            _pbar = self._progressbars[obj_id] = None
            if desc is None:
                desc = "Progress"

        if _pbar is None:
            if obj.parent_viewer is not None:
                _pbar = NapariProgressBar(value=0, max=total)
            else:
                _pbar = ProgressBar(value=0, max=total)
                _pbar.native.setParent(obj.native, _pbar.native.windowFlags())
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
        pbar = pbar._labeled_widget()
    pbar.close()
    return None


def increment(pbar: _SupportProgress):
    """Increment progressbar."""
    if pbar.value == pbar.max:
        pbar.max = 0
    else:
        pbar.value += 1
    return None
