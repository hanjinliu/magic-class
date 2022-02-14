# Most of the part copied from "magicgui.tqdm".
from __future__ import annotations
from typing import Iterable, cast
import inspect
from magicgui.application import use_app
from magicgui.widgets import ProgressBar as _ProgressBar, FunctionGui
from magicgui.tqdm import _find_calling_function_gui

try:
    from tqdm import tqdm as _tqdm_std
except ImportError as e:  # pragma: no cover
    msg = f"{e}. To use magicclass with tqdm please `pip install tqdm`"
    raise type(e)(msg)


class ProgressBar(_ProgressBar):
    def tqdm(self, iterable=None, *args, **kwargs):
        return tqdm(iterable=iterable, *args, pbar=self, **kwargs)

    def trange(self, *args, **kwargs):
        return self.tqdm(range(*args), **kwargs)


_tqdm_kwargs = {
    p.name
    for p in inspect.signature(_tqdm_std.__init__).parameters.values()
    if p.kind is not inspect.Parameter.VAR_KEYWORD and p.name != "self"
}


class tqdm(_tqdm_std):
    """
    Re-implementation of ``magicgui``'s ``tqdm``.
    """

    disable: bool

    def __init__(
        self, iterable: Iterable = None, *args, pbar: _ProgressBar = None, **kwargs
    ) -> None:
        kwargs = kwargs.copy()
        pbar_kwargs = {k: kwargs.pop(k) for k in set(kwargs) - _tqdm_kwargs}
        self._mgui = _find_calling_function_gui(max_depth=10)

        kwargs["gui"] = True
        kwargs.setdefault("mininterval", 0.025)
        super().__init__(iterable, *args, **kwargs)

        self.prefix = kwargs.get("prefix", "")
        self.sp = lambda x: None  # no-op status printer, required for older tqdm compat

        # check if we're being instantiated inside of a magicgui container
        if pbar is None:
            self.progressbar = self._get_progressbar(**pbar_kwargs)
        elif isinstance(pbar, _ProgressBar):
            self.progressbar = pbar
        else:
            raise TypeError("'pbar' must be a ProgressBar widget if given.")

        if self.disable:
            return

        self._pbar_was_visible = self.progressbar.visible
        self._pbar_old_label = self.progressbar.label

        self._app = use_app()

        if self.total is not None:
            # initialize progress bar range
            self.progressbar.range = (self.n, self.total)
            self.progressbar.value = self.n
        else:
            # show a busy indicator instead of a percentage of steps
            self.progressbar.range = (0, 0)
        self.progressbar.show()

    @property
    def _in_visible_gui(self) -> bool:
        try:
            return self._mgui is not None and self._mgui.visible
        except RuntimeError:
            return False

    def _get_progressbar(self, **kwargs) -> _ProgressBar:
        """Create ProgressBar or get from the parent gui `_tqdm_pbars` deque.

        The deque allows us to create nested iterables inside of a magigui, while
        resetting and reusing progress bars across ``FunctionGui`` calls. The nesting
        depth (into the deque) is reset by :meth:`FunctionGui.__call__`, right before
        the function is called.  Then, as the function encounters `tqdm` instances,
        this method gets or creates a progress bar and increment the
        :attr:`FunctionGui._tqdm_depth` counter on the ``FunctionGui``.
        """
        if self._mgui is None:
            return _ProgressBar(**kwargs)

        if len(self._mgui._tqdm_pbars) > self._mgui._tqdm_depth:
            pbar = self._mgui._tqdm_pbars[self._mgui._tqdm_depth]
        else:
            pbar = _ProgressBar(**kwargs)
            self._mgui._tqdm_pbars.append(pbar)
            self._mgui.append(pbar)
        self._mgui._tqdm_depth += 1
        return pbar

    def display(self, msg: str = None, pos: int = None) -> None:
        """Update the display."""
        if not (self._in_visible_gui or self.progressbar.visible):
            return super().display(msg=msg, pos=pos)

        self.progressbar.value = self.n
        if self.prefix:
            self.progressbar.label = self.prefix
        self._app.process_events()

    def close(self) -> None:
        """Cleanup and (if leave=False) close the progressbar."""
        if not self._pbar_was_visible:
            self.progressbar.hide()
        self.progressbar.label = self._pbar_old_label
        if not self._in_visible_gui:
            return super().close()
        self._mgui = cast(FunctionGui, self._mgui)

        if self.disable:
            return

        # Prevent multiple closures
        self.disable = True

        # remove from tqdm instance set
        with self._lock:
            try:
                self._instances.remove(self)
            except KeyError:  # pragma: no cover
                pass

            if not self.leave:
                self._app.process_events()
                self.progressbar.hide()

        self._mgui._tqdm_depth -= 1

    def __enter__(self):
        return self.progressbar


def trange(*args, **kwargs) -> tqdm:
    """Shortcut for ``tqdm(range(*args), **kwargs)``."""
    return tqdm(range(*args), **kwargs)
