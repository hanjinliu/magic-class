from __future__ import annotations
import sys
import logging
from contextlib import contextmanager
from qtpy import QtWidgets as QtW, QtGui
from magicgui.backends._qtpy.widgets import QBaseWidget
from magicgui.widgets import Widget
import logging

# See https://stackoverflow.com/questions/28655198/best-way-to-display-logs-in-pyqt


class QtLogger(QtW.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setReadOnly(True)

    def printText(self, text: str):
        self.moveCursor(QtGui.QTextCursor.End)
        self.insertPlainText(text)
        self.moveCursor(QtGui.QTextCursor.End)


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
        with logger.set_stdout():
            print("text")
            function_that_print_something()

        # permanently change the destination of print function
        sys.stdout = logger

    Logging in the widget

    .. code-block:: python

        with logger.set_logger():
            function_that_log_something()

        logging.getLogger().addHandler(logger)

    """

    def __init__(self):
        logging.Handler.__init__(self)
        super().__init__(widget_type=QBaseWidget, backend_kwargs={"qwidg": QtLogger})

    def emit(self, record):
        msg = self.format(record)
        self.print(msg)

    def print(self, *msg, sep=" ", end="\n"):
        self._widget._qwidget.printText(sep.join(msg) + end)

    def print_html(self, html: str):
        self._widget._qwidget.addHtml(html)

    def write(self, msg):
        self.print(msg, end="")

    def flush(self):
        pass

    @contextmanager
    def set_stdout(self):
        """A context manager for printing things in this widget."""
        sys.stdout = self
        yield self
        sys.stdout = sys.__stdout__

    @contextmanager
    def set_logger(self):
        """A context manager for logging things in this widget."""
        logging.getLogger().addHandler(self)
        yield self
        logging.getLogger().removeHandler(self)
