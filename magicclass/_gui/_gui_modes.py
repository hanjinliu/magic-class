from __future__ import annotations

from types import TracebackType
from contextlib import contextmanager
from typing import Callable, TYPE_CHECKING
from enum import Enum
from pathlib import Path
import functools

from magicgui.widgets import Widget
from .mgui_ext import FunctionGuiPlus
from magicclass._exceptions import Canceled

if TYPE_CHECKING:
    from ._base import BaseGui


class PopUpMode(Enum):
    """Define how to popup FunctionGui."""

    popup = "popup"
    first = "first"
    last = "last"
    above = "above"
    below = "below"
    dock = "dock"
    dialog = "dialog"
    parentlast = "parentlast"
    parentsub = "parentsub"

    def need_title_bar(self) -> bool:
        """Whethre the popup widget needs a custom title bar"""
        return self not in {
            PopUpMode.popup,
            PopUpMode.dock,
            PopUpMode.parentsub,
            PopUpMode.dialog,
        }

    def activate_magicgui(self, mgui: FunctionGuiPlus, parent: Widget):
        """Mode specific methods to activate magicgui."""
        if self not in (
            PopUpMode.dock,
            PopUpMode.dialog,
            PopUpMode.parentsub,
        ):
            mgui.show()
        elif self is PopUpMode.dock:
            mgui.native.parent().show()  # show dock widget
        elif self is PopUpMode.parentsub:
            mgui.native.parent().setVisible(True)
        else:
            mgui.exec_as_dialog(parent=parent)
        try:
            mgui[0].native.setFocus()
        except Exception:
            pass

    def connect_close_callback(self, mgui: FunctionGuiPlus):
        """Connect mode specific closed callbacks to magicgui."""
        if self not in {PopUpMode.dock, PopUpMode.parentsub, PopUpMode.dialog}:
            mgui.calling.connect(mgui.hide)
        elif self in {PopUpMode.dock, PopUpMode.parentsub}:
            # If FunctioGui is docked or in a subwindow, we should close
            # the parent QDockWidget/QMdiSubwindow.
            mgui.calling.connect(lambda: mgui.native.parent().hide())


def _msgbox_raising(e: Exception, parent: Widget):
    from ._message_box import QtErrorMessageBox

    return QtErrorMessageBox.raise_(e, parent=parent.native)


def _stderr_raising(e: Exception, parent: Widget):
    raise e


def _napari_notification_raising(e: Exception, parent: Widget):
    from napari.utils.notifications import show_error

    return show_error(str(e))


def _debug_raising(e: Exception, parent: Widget):
    from magicclass.testing import GuiErrorMonitor

    monitor = GuiErrorMonitor.get_instance(parent)
    with monitor.catch():
        raise e


class ErrorMode(Enum):
    """Mode to handle error raised in magicclass during manual operations."""

    msgbox = "msgbox"
    stderr = "stderr"
    stdout = "stdout"
    napari = "napari"
    debug = "debug"
    ignore = "ignore"

    def get_handler(self):
        """Get error handler."""
        return ErrorModeHandlers[self]

    @classmethod
    def wrap_handler(cls, func: Callable, parent: BaseGui):
        """Wrap function with the error handler."""

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            handler = parent._error_mode.get_handler()
            try:
                out = func(*args, **kwargs)
            except Canceled as e:
                out = e  # Do not raise "Canceled" message box
            except Exception as e:
                cls.cleanup_tb(e)
                handler(e, parent=parent)
                out = e
            return out

        return wrapped_func

    @classmethod
    def cleanup_tb(cls, e: Exception) -> Exception:
        """Cleanup traceback."""
        e.__traceback__ = _cleanup_tb(e.__traceback__)
        return e

    @classmethod
    @contextmanager
    def raise_with_handler(cls, parent: BaseGui, reraise: bool = True):
        """Raise error with the error handler in this context."""
        try:
            yield
        except Exception as e:
            parent._error_mode.get_handler()(e, parent=parent)
            if reraise:
                raise e


ErrorModeHandlers = {
    ErrorMode.msgbox: _msgbox_raising,
    ErrorMode.stderr: _stderr_raising,
    ErrorMode.stdout: lambda e, parent: print(f"{e.__class__.__name__}: {e}"),
    ErrorMode.napari: _napari_notification_raising,
    ErrorMode.debug: _debug_raising,
    ErrorMode.ignore: lambda e, parent: None,
}


def _cleanup_tb(tb: TracebackType) -> TracebackType:
    """Remove useless info from a traceback object."""
    current_tb = tb
    while current_tb is not None:
        if current_tb.tb_frame.f_code.co_name == "_recordable":
            tb = current_tb.tb_next
            break
        current_tb = current_tb.tb_next

    # cleanup exceptions from qthreading
    current_tb = tb
    tb_list: list[TracebackType] = []
    while current_tb is not None:
        path = Path(current_tb.tb_frame.f_code.co_filename).as_posix()
        if path.endswith(
            (
                "magic-class/magicclass/utils/qthreading/thread_worker.py",
                "superqt/utils/_qthreading.py",
            )
        ):
            pass
        else:
            tb_list.append(current_tb)
        current_tb = current_tb.tb_next
    nlist = len(tb_list)

    if nlist > 1:
        tb = tb_list[0]
        for i in range(nlist - 1):
            path = Path(tb_list[i].tb_frame.f_code.co_filename).as_posix()
            tb_list[i].tb_next = tb_list[i + 1]
    return tb
