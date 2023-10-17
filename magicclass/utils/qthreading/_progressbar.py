from __future__ import annotations
from contextlib import suppress
import threading
import time
from timeit import default_timer
from typing import (
    Callable,
    TYPE_CHECKING,
    Union,
    Protocol,
    runtime_checkable,
    TypedDict,
)

from qtpy.QtCore import Qt
from superqt.utils import GeneratorWorker, FunctionWorker
from magicgui.widgets import ProgressBar, Container, PushButton, Label

from magicclass.utils.qt import move_to_screen_center
from magicclass.utils.qtsignal import QtSignal
from magicclass.utils.qthreading._callback import NestedCallback
from magicclass.widgets.containers import FrameContainer

if TYPE_CHECKING:
    from magicclass.fields import MagicField


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
        """Return the current progress."""
        raise NotImplementedError()

    @value.setter
    def value(self, v) -> None:
        """Set the current progress."""
        raise NotImplementedError()

    @property
    def max(self) -> int:
        """Return the maximum progress value."""
        raise NotImplementedError()

    @max.setter
    def max(self, v) -> None:
        """Set the maximum progress value."""
        raise NotImplementedError()

    def set_description(self, desc: str):
        """Set the description of the progressbar."""
        raise NotImplementedError()

    def show(self):
        """Show the progressbar."""
        raise NotImplementedError()

    def close(self):
        """Close the progressbar."""
        raise NotImplementedError()


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
        """Return the current progress."""
        raise NotImplementedError()

    @value.setter
    def value(self, v) -> None:
        """Set the current progress."""
        raise NotImplementedError()

    @property
    def max(self) -> int:
        """Return the maximum progress value."""
        raise NotImplementedError()

    @max.setter
    def max(self, v) -> None:
        """Set the maximum progress value."""
        raise NotImplementedError()

    def set_description(self, desc: str):
        """Set the description of the progressbar."""
        raise NotImplementedError()

    def show(self):
        """Show the progressbar."""
        raise NotImplementedError()

    def close(self):
        """Close the progressbar."""
        raise NotImplementedError()

    def increment(self):
        """Increment the progressbar"""
        raise NotImplementedError()


ProgressBarLike = Union[ProgressBar, _SupportProgress]


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
        return None

    def close(self):
        return self._pbar.close()

    def increment(self, yielded=None):
        if isinstance(yielded, NestedCallback):
            return None
        return self._pbar.increment_with_overflow()


class Timer:
    """A timer class with intuitive API."""

    def __init__(self):
        self._t0 = default_timer()
        self._t_total = 0.0
        self._running = False

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
        return self.__init__()

    def format_time(self, fmt: str = "{hour:0>2}:{min:0>2}:{sec:0>2}") -> str:
        """Format current time."""
        min_all, sec = divmod(self.sec, 60)
        hour, min = divmod(min_all, 60)
        return fmt.format(hour=int(hour), min=int(min), sec=int(sec))


class _ProgressBarContainer(Container["DefaultProgressBar"]):
    def __init__(self):
        super().__init__(labels=False)
        self.margins = (2, 2, 2, 2)
        self.native.setWindowTitle("Progress")
        self.native.layout().setAlignment(Qt.AlignmentFlag.AlignTop)


class DefaultProgressBar(FrameContainer, _SupportProgress):
    """The default progressbar widget."""

    # The outer container
    _CONTAINER = _ProgressBarContainer()

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
        self.pbar.min_width = 240
        self._timer = Timer()
        self._time_signal = QtSignal()
        self._time_signal.connect(self._on_timer_updated)

        self._running = False
        self._thread_timer: threading.Thread | None = None

        super().__init__(widgets=[self.progress_label, self.pbar, cnt], labels=False)

        self.hide_footer()
        self.time_label.visible = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(title={self.name!r})"

    def _on_timer_updated(self, _=None):
        with suppress(RuntimeError):
            if self._timer.sec < 3600:
                self.time_label.value = self._timer.format_time("{min:0>2}:{sec:0>2}")
            else:
                self.time_label.value = self._timer.format_time()
            if not self.time_label.visible:
                self.time_label.visible = True
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
        with suppress(RuntimeError):
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
        """True if paused."""
        return not self._timer._running

    @property
    def value(self) -> int:
        """Progress bar value."""
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

    def show(self):
        parent = self.native.parent()
        with suppress(RuntimeError):
            if _is_main_thread():
                self._CONTAINER.append(self)
                if self._CONTAINER.native.parent() is not parent:
                    self._CONTAINER.native.setParent(
                        parent,
                        self._CONTAINER.native.windowFlags(),
                    )
            if not self._CONTAINER.visible:
                self._CONTAINER.show()
                move_to_screen_center(self._CONTAINER.native)
        return None

    def close(self):
        i = -1
        for i, wdt in enumerate(self._CONTAINER):
            if wdt is self:
                break
        super().close()
        if i < 0:
            return None
        with suppress(RuntimeError):
            if _is_main_thread():
                self._CONTAINER.pop(i)
                self._CONTAINER.height = 1  # minimize height
                if len(self._CONTAINER) == 0:
                    self._CONTAINER.close()
        return None

    def increment(self, yielded=None):
        """Increment progressbar."""
        if isinstance(yielded, NestedCallback):
            return None
        with suppress(RuntimeError):
            if self.value == self.max:
                self.max = 0
            else:
                self.value += 1
        return None

    def hide_footer(self):
        self.footer[1].visible = self.footer[2].visible = False

    def show_footer(self):
        self.footer[1].visible = self.footer[2].visible = True

    def set_description(self, desc: str):
        """Set description as the label of the progressbar."""
        self.progress_label.value = desc
        return None

    def set_title(self, title: str):
        """Set the groupbox title."""
        self.name = title
        return None

    def set_worker(self, worker: GeneratorWorker | FunctionWorker):
        """Set currently running worker."""
        self._worker = worker
        self._worker.finished.connect(self._finish)
        self._worker.started.connect(self._start_thread)
        if not isinstance(self._worker, GeneratorWorker):
            # FunctionWorker does not have yielded/aborted signals.
            self.hide_footer()
            return None
        self.show_footer()
        self.time_label.visible = True

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


def _is_main_thread() -> bool:
    """True if the current thread is the main thread."""
    return threading.current_thread().name == "MainThread"
