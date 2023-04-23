from __future__ import annotations
from types import TracebackType

from typing import Callable
from enum import Enum
import functools
from magicgui.widgets import FunctionGui, Widget
from .mgui_ext import FunctionGuiPlus


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
        return self not in {
            PopUpMode.popup,
            PopUpMode.dock,
            PopUpMode.parentsub,
            PopUpMode.dialog,
        }

    def activate_magicgui(self, mgui: FunctionGuiPlus):
        if self not in (
            PopUpMode.dock,
            PopUpMode.dialog,
            PopUpMode.parentsub,
        ):
            mgui.show()
        elif self is PopUpMode.dock:
            mgui.parent.show()  # show dock widget
        elif self is PopUpMode.parentsub:
            mgui.native.parent().setVisible(True)
        else:
            mgui.exec_as_dialog(parent=self)
        try:
            mgui[0].native.setFocus()
        except Exception:
            pass

    def connect_close_callback(self, mgui: FunctionGui):
        if self not in {PopUpMode.dock, PopUpMode.parentsub, PopUpMode.dialog}:
            mgui.called.connect(mgui.hide)
        elif self in {PopUpMode.dock, PopUpMode.parentsub}:
            # If FunctioGui is docked or in a subwindow, we should close
            # the parent QDockWidget/QMdiSubwindow.
            mgui.called.connect(lambda: mgui.parent.hide())


def _msgbox_raising(e: Exception, parent: Widget):
    from ._message_box import QtErrorMessageBox

    return QtErrorMessageBox.raise_(e, parent=parent.native)


def _stderr_raising(e: Exception, parent: Widget):
    pass


def _stdout_raising(e: Exception, parent: Widget):
    print(f"{e.__class__.__name__}: {e}")


def _napari_notification_raising(e: Exception, parent: Widget):
    from napari.utils.notifications import show_error

    return show_error(str(e))


class ErrorMode(Enum):
    msgbox = "msgbox"
    stderr = "stderr"
    stdout = "stdout"
    napari = "napari"

    def get_handler(self):
        """Get error handler."""
        return ErrorModeHandlers[self]

    def wrap_handler(self, func: Callable, parent):
        """Wrap function with the error handler."""
        handler = self.get_handler()

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            try:
                out = func(*args, **kwargs)
            except Exception as e:
                e.__traceback__ = _cleanup_tb(e.__traceback__)
                handler(e, parent=parent)
                out = e
            return out

        return wrapped_func


ErrorModeHandlers = {
    ErrorMode.msgbox: _msgbox_raising,
    ErrorMode.stderr: _stderr_raising,
    ErrorMode.stdout: _stdout_raising,
    ErrorMode.napari: _napari_notification_raising,
}


def _cleanup_tb(tb: TracebackType):
    """Remove useless info from a traceback object."""
    current_tb = tb
    while current_tb is not None:
        if current_tb.tb_frame.f_code.co_name == "_recordable":
            tb = current_tb.tb_next
            break
        current_tb = current_tb.tb_next
    return tb
