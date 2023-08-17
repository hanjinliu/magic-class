from __future__ import annotations

from contextlib import suppress, contextmanager
import inspect
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
    overload,
    TypeVar,
    Generic,
    Protocol,
)
from typing_extensions import ParamSpec
import warnings

from superqt.utils import create_worker, GeneratorWorker, FunctionWorker
from qtpy.QtCore import Qt, QThread, QCoreApplication
from magicgui.widgets import ProgressBar, Widget
from magicgui.application import use_app

from magicclass.utils._functions import get_signature

from magicclass.undo import UndoCallback

from ._progressbar import (
    DefaultProgressBar,
    NapariProgressBar,
    _SupportProgress,
    ProgressDict,
    ProgressBarLike,
)
from ._callback import CallbackList, Callback

if TYPE_CHECKING:
    from magicclass._gui import BaseGui
    from magicclass._gui.mgui_ext import Clickable
    from magicclass.fields import MagicField
    from typing_extensions import Self


_P = ParamSpec("_P")
_R = TypeVar("_R")


class Aborted(RuntimeError):
    """Raised when worker is aborted."""

    @classmethod
    def raise_(cls, *args):
        """A function version of "raise"."""
        if not args:
            args = ("Aborted.",)
        raise cls(*args)


class AsyncMethod(Protocol[_P, _R]):
    """A protocol for async method."""

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        ...

    __thread_worker__: thread_worker[_P]


if TYPE_CHECKING:

    def _async_method(func: Callable[_P, _R]) -> AsyncMethod[_P, _R]:
        ...

else:
    _async_method = lambda f: f


class thread_worker(Generic[_P]):
    """Create a worker in a superqt/napari style."""

    _DEFAULT_PROGRESS_BAR = DefaultProgressBar
    _DEFAULT_TOTAL = 0
    _WINDOW_FLAG = Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.Window  # fmt: skip
    _BLOCKING_SOURCES = []

    def __init__(
        self,
        f: Callable[_P, _R] | None = None,
        *,
        ignore_errors: bool = False,
        progress: ProgressDict | bool | None = None,
    ) -> None:
        self._func: Callable[_P, _R] | None = None
        self._callback_dict_ = {
            "started": CallbackList(),
            "returned": CallbackList(),
            "errored": CallbackList(),
            "yielded": CallbackList(),
            "finished": CallbackList(),
            "aborted": CallbackList(),
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
            progress.setdefault("total", self.__class__._DEFAULT_TOTAL)
            progress.setdefault("pbar", None)

        self._progress: ProgressDict | None = progress

    @property
    def func(self) -> Callable[_P, _R]:
        """The original function."""
        return self._func

    @classmethod
    def with_progress(
        cls,
        desc: str | Callable | None = None,
        total: str | Callable | int | None = None,
        pbar: ProgressBar | _SupportProgress | MagicField | None = None,
        **kwargs,
    ) -> Self:
        """
        Configure the progressbar.

        Parameters
        ----------
        desc : str or callable
            The description of the progressbar. If a callable is given, it will be
            called to get the description.
        total : str, int or callable
            Total iteration of the progressbar. If a callable is given, it will be
            called to get the total iteration. If str is given, it will be evaluated
            with the function's arguments.
        pbar : ProgressBar or MagicField
            Progressbar object.
        """
        self = cls()
        if total is None:
            total = cls._DEFAULT_TOTAL
        progress = dict(desc=desc, total=total, pbar=pbar, **kwargs)

        self._progress = progress
        return self

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

    @staticmethod
    def to_callback(callback: Callable, *args, **kwargs) -> Callback:
        warnings.warn(
            "Defining callback with to_callback is deprecated because its "
            "behavior is confusing. Use thread_worker.callback instead.",
            DeprecationWarning,
        )
        cb = _CallbackDeprecated(callback)
        if args or kwargs:
            cb = cb(*args, **kwargs)
        return cb

    @staticmethod
    def callback(callback: Callable) -> Callback:
        """Convert a callback function to a callback object."""
        return Callback(callback)

    @classmethod
    @contextmanager
    def blocking_mode(cls):
        cls._BLOCKING_SOURCES.append(None)
        try:
            yield
        finally:
            cls._BLOCKING_SOURCES.pop()

    @property
    def is_generator(self) -> bool:
        """True if bound function is a generator function."""
        return inspect.isgeneratorfunction(self._func)

    @property
    def __is_recordable__(self) -> bool:
        return self._recorder is not None

    @property
    def __doc__(self) -> str:
        """Synchronize docstring with bound function."""
        return self.func.__doc__

    @__doc__.setter
    def __doc__(self, doc: str):
        self.func.__doc__ = doc

    def _set_recorder(self, recorder: Callable[_P, Any]):
        """
        Set macro recorder function.
        Must accept ``recorder(bgui, *args, **kwargs)``.
        """
        self._recorder = recorder
        return None

    @overload
    def __call__(self, f: Callable[_P, _R]) -> thread_worker[_P]:
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

    def __get__(self, gui: BaseGui, objtype=None) -> Callable[_P, Any]:
        if gui is None:
            return self

        gui_id = id(gui)
        if gui_id in self._objects:
            return self._objects[gui_id]

        _create_worker = self._create_method(gui)
        _create_worker.__signature__ = self._get_method_signature()

        self._objects[gui_id] = _create_worker  # cache
        return _create_worker

    def button(self, gui: BaseGui) -> Clickable:
        """The corresponding button object."""
        return gui[self._func.__name__]

    def _create_qt_worker(
        self, gui: BaseGui, *args, **kwargs
    ) -> FunctionWorker | GeneratorWorker:
        """Create a worker object."""
        if self.is_generator:

            def _run(*args, **kwargs):
                with gui.macro.blocked():
                    out = yield from self._func.__get__(gui)(*args, **kwargs)
                return out

        else:

            def _run(*args, **kwargs):
                with gui.macro.blocked():
                    out = self._func.__get__(gui)(*args, **kwargs)
                return out

        worker = create_worker(
            _run,
            _ignore_errors=True,  # NOTE: reraising is processed in _create_method
            _start_thread=False,
            *args,
            **kwargs,
        )

        return worker

    def _create_qt_generator_worker(
        self, gui: BaseGui, *args, **kwargs
    ) -> GeneratorWorker:
        def _run():
            with gui.macro.blocked():
                if self.is_generator:
                    out = yield from self._func.__get__(gui)(*args, **kwargs)
                else:
                    out = self._func.__get__(gui)(*args, **kwargs)
                yield out

        worker = create_worker(
            _run,
            _ignore_errors=True,  # NOTE: reraising is processed in _create_method
            _start_thread=False,
            *args,
            **kwargs,
        )

        return worker

    def _create_method(self, gui: BaseGui) -> Callable[_P, None]:
        @_async_method
        @wraps(self)
        def _create_worker(*args, **kwargs):
            _is_non_blocking = (
                self.button(gui).running and len(self._BLOCKING_SOURCES) == 0
            )
            # create a worker object
            worker = self._create_qt_worker(gui, *args, **kwargs)
            is_generator = isinstance(worker, GeneratorWorker)
            pbar: _SupportProgress | None = None
            if self._progress:
                pbar = self._init_pbar_for_args(gui, args, kwargs)
                worker.started.connect(init_pbar.__get__(pbar))

            self._bind_callbacks(worker, gui, args, kwargs)

            if self._progress:
                self._init_pbar_post(pbar, worker)

            if is_generator:

                @worker.aborted.connect
                def _on_abort():
                    gui._error_mode.wrap_handler(Aborted.raise_, parent=gui)()
                    gui.macro.active = True
                    Aborted.raise_()

            if _is_non_blocking:

                @worker.errored.connect
                def _on_error(err: Exception):
                    # NOTE: Exceptions are raised in other thread so context manager
                    # cannot catch them. Macro has to be reactived here.
                    gui._error_mode.cleanup_tb(err)
                    gui._error_mode.get_handler()(err, parent=gui)
                    if not self._ignore_errors:
                        raise err  # reraise

                return worker.start()
            else:
                # If function is called from script, some events must get processed by
                # the application while keep script stopping at each line of code.
                return self._run_blocked(gui, worker, pbar)

        _create_worker.__self__ = gui
        _create_worker.__thread_worker__ = self
        return _create_worker

    def _run_blocked(
        self,
        gui: BaseGui,
        worker: FunctionWorker | GeneratorWorker,
        pbar: ProgressBar | None,
    ):
        app = use_app()

        if isinstance(pbar, DefaultProgressBar):
            pbar.pause_button.enabled = False
        worker.started.connect(app.process_events)
        worker.finished.connect(app.process_events)

        _empty = object()
        result = err = _empty

        @worker.returned.connect
        def _(val):
            nonlocal result
            result = val

        @worker.errored.connect
        def _(exc):
            nonlocal err
            err = gui._error_mode.cleanup_tb(exc)

        if isinstance(worker, GeneratorWorker):

            @worker.aborted.connect
            def _():
                nonlocal err
                err = Aborted()

        if isinstance(worker, GeneratorWorker):
            worker.yielded.connect(app.process_events)
        try:
            worker.run()

        except KeyboardInterrupt as e:
            if isinstance(pbar, DefaultProgressBar):
                pbar._abort_worker()
            else:
                worker.quit()
            worker.finished.emit()
            gui._error_mode.wrap_handler(Aborted.raise_, parent=gui)()
            raise e

        if result is _empty and err is not _empty:
            raise err
        if isinstance(result, UndoCallback):
            return result.return_value
        return result

    def _get_method_signature(self) -> inspect.Signature:
        sig = self.__signature__
        params = list(sig.parameters.values())[1:]
        return sig.replace(parameters=params)

    def _init_pbar_for_args(self, gui, args, kwargs) -> _SupportProgress:
        # prepare progress bar
        _pbar = self._progress["pbar"]
        desc, total = self._normalize_desc_and_total(gui, *args, **kwargs)
        if not self.is_generator:
            total = self._DEFAULT_TOTAL

        # create progressbar widget (or any proper widget)
        if _pbar is None:
            pbar = self._find_progressbar(gui, desc=desc, total=total)
        elif isinstance(_pbar, MagicField):
            pbar = _pbar.get_widget(gui)
            if not isinstance(pbar, ProgressBar):
                raise TypeError(f"{_pbar.name} does not create a ProgressBar.")
            pbar.label = desc or _pbar.name
            pbar.max = total
        else:
            pbar = _pbar
            pbar.set_description(desc)
        return pbar

    def _init_pbar_post(self, pbar: _SupportProgress, worker: GeneratorWorker):
        if not getattr(pbar, "visible", False):
            # return the progressbar to the initial state
            worker.finished.connect(close_pbar.__get__(pbar))
        if pbar.max != 0 and self.is_generator:
            worker.pbar = pbar  # avoid garbage collection
            worker.yielded.connect(increment.__get__(pbar))

        if hasattr(pbar, "set_worker"):
            # if _SupportProgress object support set_worker
            pbar.set_worker(worker)
        if hasattr(pbar, "set_title"):
            pbar.set_title(self._func.__name__.replace("_", " "))

    def _bind_callbacks(
        self,
        worker: FunctionWorker | GeneratorWorker,
        gui: BaseGui,
        args,
        kwargs,
    ):
        # bind callbacks
        is_generator = isinstance(worker, GeneratorWorker)
        for c in self.started._iter_as_method(gui):
            worker.started.connect(c)
        for c in self.returned._iter_as_method(gui):
            worker.returned.connect(c)
        cb_returned = partial(
            Callback.catch,
            gui=gui,
            tw=self,
            args=args,
            kwargs=kwargs,
        )
        worker.returned.connect(cb_returned)
        for c in self.errored._iter_as_method(gui):
            worker.errored.connect(c)
        for c in self.finished._iter_as_method(gui):
            worker.finished.connect(c)

        if is_generator:
            for c in self.aborted._iter_as_method(gui):
                worker.aborted.connect(c)
            for c in self.yielded._iter_as_method(gui):
                worker.yielded.connect(c)
            cb_yielded = self._create_callback_yielded(gui, args, kwargs)
            worker.yielded.connect(cb_yielded)

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
        from magicclass.fields import MagicField

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
            if isinstance(_pbar, Widget) and _pbar.parent is None and _is_main_thread():
                # Popup progressbar as a splashscreen if it is not a child widget.
                _pbar.native.setParent(gui.native, self.__class__._WINDOW_FLAG)

        else:
            _pbar.max = total

        # try to set description
        if hasattr(_pbar, "set_description"):
            _pbar.set_description(desc)
        else:
            _pbar.label = desc
        return _pbar

    def _normalize_desc_and_total(self, gui, *args, **kwargs):
        _desc = self._progress["desc"]
        _total = self._progress["total"]

        all_args = None  # all the argument of the function
        # progress bar description
        if callable(_desc):
            arguments = self.__signature__.bind(gui, *args, **kwargs)
            arguments.apply_defaults()
            all_args = arguments.arguments
            desc = _desc(**_filter_args(_desc, all_args))
        else:
            desc = str(_desc or self._func.__name__)

        # total number of steps
        if isinstance(_total, str) or callable(_total):
            if all_args is None:
                arguments = self.__signature__.bind(gui, *args, **kwargs)
                arguments.apply_defaults()
                all_args = arguments.arguments
            if isinstance(_total, str):
                total = eval(_total, {}, all_args)
            elif callable(_total):
                total = _total(**_filter_args(_total, all_args))
            else:
                raise RuntimeError("Unreachable.")
        elif isinstance(_total, int):
            total = _total
        else:
            raise TypeError("'total' must be int, callable or evaluatable string.")

        return desc, total

    @property
    def started(self) -> CallbackList[None]:
        """Event that will be emitted on started."""
        return self._callback_dict_["started"]

    @property
    def returned(self) -> CallbackList[_R]:
        """Event that will be emitted on returned."""
        return self._callback_dict_["returned"]

    @property
    def errored(self) -> CallbackList[Exception]:
        """Event that will be emitted on errored."""
        return self._callback_dict_["errored"]

    @property
    def yielded(self) -> CallbackList[_R]:
        """Event that will be emitted on yielded."""
        if not self.is_generator:
            raise TypeError(
                f"Worker of non-generator function {self._func!r} does not have "
                "yielded signal."
            )
        return self._callback_dict_["yielded"]

    @property
    def finished(self) -> CallbackList[None]:
        """Event that will be emitted on finished."""
        return self._callback_dict_["finished"]

    @property
    def aborted(self) -> CallbackList[None]:
        """Event that will be emitted on aborted."""
        if not self.is_generator:
            raise TypeError(
                f"Worker of non-generator function {self._func!r} does not have "
                "aborted signal."
            )
        return self._callback_dict_["aborted"]

    def _create_callback_yielded(self, gui: BaseGui, args, kwargs):
        def cb(out: Any | None):
            return Callback.catch(
                out, gui=gui, tw=self, args=args, kwargs=kwargs, record=False
            )

        return cb


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
    with suppress(RuntimeError):
        if pbar.value == pbar.max:
            pbar.max = 0
        else:
            pbar.value += 1
    return None


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


def _is_main_thread() -> bool:
    """True if the current thread is the main thread."""
    return QThread.currentThread() is QCoreApplication.instance().thread()


class _CallbackDeprecated(Callback):
    def __call__(self, *args, **kwargs) -> Callback:
        """Return a partial callback."""
        return self.__class__(partial(self._func, *args, **kwargs))


to_callback = thread_worker.to_callback  # function version
