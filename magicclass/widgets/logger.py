from __future__ import annotations
import sys
import logging
from contextlib import contextmanager
from qtpy import QtWidgets as QtW, QtGui
from magicgui.backends._qtpy.widgets import QBaseWidget
from magicgui.widgets import Widget
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

# See https://stackoverflow.com/questions/28655198/best-way-to-display-logs-in-pyqt


class QtLogger(QtW.QTextEdit):
    def __init__(self, parent=None, max_history: int = 500):
        super().__init__(parent=parent)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WordWrap)
        self._max_history = int(max_history)
        self._n_lines = 0

    def appendText(self, text: str):
        self.moveCursor(QtGui.QTextCursor.End)
        self.insertPlainText(text)
        self.moveCursor(QtGui.QTextCursor.End)
        self._post_append()

    def appendHtml(self, html: str):
        self.moveCursor(QtGui.QTextCursor.End)
        self.insertHtml(html)
        self.moveCursor(QtGui.QTextCursor.End)
        self._post_append()

    def appendImage(self, qimage):
        cursor = self.textCursor()
        cursor.insertImage(qimage)
        self.insertPlainText("\n\n")
        self._post_append()

    def _post_append(self):
        if self._n_lines < self._max_history:
            self._n_lines += 1
            return None
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.Start)
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.movePosition(QtGui.QTextCursor.Down)
        cursor.deletePreviousChar()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(cursor)
        return None


class Logger(Widget, logging.Handler):
    """
    A widget for logging.

    Examples
    --------

    Create widget as other ``magicgui`` or ``magicclass`` widgets.

    .. code-block:: python

        logger = Logger(name="my logger")  # magicgui way

        # magicclass way
        @magicclass
        class Main:
            logger = field(Logger, name="my logger")

        # This is OK
        @magicclass
        class Main:
            logger = Logger()


    Print something in the widget

    .. code-block:: python

        # print something in the widget.
        logger.print("text")

        # a context manager that change the destination of print function.
        with logger.set_as_stdout():
            print("text")
            function_that_print_something()

        # permanently change the destination of print function
        sys.stdout = logger

    Logging in the widget

    .. code-block:: python

        with logger.set_as_logger():
            function_that_log_something()

        logging.getLogger().addHandler(logger)

    """

    def __init__(self):
        logging.Handler.__init__(self)
        super().__init__(widget_type=QBaseWidget, backend_kwargs={"qwidg": QtLogger})

    def emit(self, record):
        msg = self.format(record)
        self.print(msg)

    def clear(self):
        self._widget._qwidget.clear()
        return None

    def print(self, *msg, sep=" ", end="\n"):
        self._widget._qwidget.appendText(sep.join(map(str, msg)) + end)
        return None

    def print_html(self, html: str):
        self._widget._qwidget.appendHtml(html)
        return None

    def print_table(self, table):
        import pandas as pd

        df = pd.DataFrame(table)
        self._widget._qwidget.appendHtml(df.to_html())
        return None

    def print_image(
        self,
        arr: np.ndarray,
        vmin=None,
        vmax=None,
        cmap=None,
        norm=None,
        width=None,
        height=None,
    ):
        from magicgui import _mpl_image

        img = _mpl_image.Image()

        img.set_data(arr)
        img.set_clim(vmin, vmax)
        img.set_cmap(cmap)
        img.set_norm(norm)

        val = img.make_image()
        image = QtGui.QImage(
            val, val.shape[1], val.shape[0], QtGui.QImage.Format_RGBA8888
        )
        if width is None:
            if height is None:
                height = 300
            image = image.scaledToHeight(height)
        else:
            image = image.scaledToWidth(width)

        self._widget._qwidget.appendImage(image)
        return None

    def write(self, msg):
        self.print(msg, end="")
        return None

    def flush(self):
        pass

    @contextmanager
    def set_as_stdout(self):
        """A context manager for printing things in this widget."""
        sys.stdout = self
        yield self
        sys.stdout = sys.__stdout__

    @contextmanager
    def set_as_logger(self):
        """A context manager for logging things in this widget."""
        logging.getLogger().addHandler(self)
        yield self
        logging.getLogger().removeHandler(self)
