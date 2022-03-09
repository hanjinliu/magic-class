from __future__ import annotations
import sys
import logging
from contextlib import contextmanager
from qtpy import QtWidgets as QtW, QtGui
from magicgui.backends._qtpy.widgets import QBaseWidget
from magicgui.widgets import Widget
import logging
from typing import TYPE_CHECKING, Any

try:
    import numpy as np
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    FigureCanvas = FigureCanvasAgg
    MATPLOTLIB_AVAILABLE = True

except ImportError:
    MATPLOTLIB_AVAILABLE = False

if TYPE_CHECKING:
    import numpy as np
    from matplotlib.figure import Figure

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

    def _get_background_color(self) -> tuple[int, int, int, int]:
        return self.palette().color(self.backgroundRole()).getRgb()


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

    current_logger: Logger | None = None

    def __init__(self):
        logging.Handler.__init__(self)
        super().__init__(widget_type=QBaseWidget, backend_kwargs={"qwidg": QtLogger})

    def emit(self, record):
        msg = self.format(record)
        self.print(msg)

    def clear(self):
        """Clear all the histories."""
        self._widget._qwidget.clear()
        return None

    def print(self, *msg, sep=" ", end="\n"):
        """Print things in the end of the logger widget."""
        self._widget._qwidget.appendText(sep.join(map(str, msg)) + end)
        return None

    def print_html(self, html: str, end="<br></br>"):
        """Print things in the end of the logger widget as a HTML string."""
        self._widget._qwidget.appendHtml(html + end)
        return None

    def print_table(self, table, header: bool = True, index: bool = True):
        """
        Print object as a table in the logger widget.

        Parameters
        ----------
        table : table-like object
            Any object that can be passed to ``pandas.DataFrame`` can be used.
        index : bool, default is True
            Whether to show the index column.
        """
        import pandas as pd

        df = pd.DataFrame(table)
        self._widget._qwidget.appendHtml(df.to_html(header=header, index=index))
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
    ) -> None:
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

    def print_figure(self, fig: Figure) -> None:
        fig.canvas.draw()
        data = np.asarray(fig.canvas.renderer.buffer_rgba(), dtype=np.uint8)
        self.print_image(data)

        return None

    def write(self, msg):
        self.print(msg, end="")
        return None

    def flush(self):
        pass

    @contextmanager
    def set_stdout(self):
        """A context manager for printing things in this widget."""
        try:
            sys.stdout = self
            yield self
        finally:
            sys.stdout = sys.__stdout__

    @contextmanager
    def set_logger(self):
        """A context manager for logging things in this widget."""
        try:
            logging.getLogger().addHandler(self)
            yield self
        finally:
            logging.getLogger().removeHandler(self)

    @contextmanager
    def set_plt(self, style=None):
        """A context manager for inline plot in the logger widget."""
        if not MATPLOTLIB_AVAILABLE:
            yield self
            return None
        self.__class__.current_logger = self
        if style is None:
            style = self._get_proper_plt_style()
        backend = mpl.get_backend()
        show._called = False
        try:
            mpl.use("module://magicclass.widgets.logger")
            with plt.style.context(style):
                yield self
        finally:
            if not show._called:
                show()
            self.__class__.current_logger = None
            mpl.use(backend)
        return None

    def _get_proper_plt_style(self) -> dict[str, Any]:
        color = self._widget._qwidget._get_background_color()
        is_dark = sum(color[:3]) < 382.5
        if is_dark:
            params = plt.style.library["dark_background"]
        else:
            keys = plt.style.library["dark_background"].keys()
            with plt.style.context("default"):
                params: dict[str, Any] = {}
                rcparams = plt.rcParams
                for key in keys:
                    params[key] = rcparams[key]
        params["figure.facecolor"] = "#00000000"
        params["axes.facecolor"] = "#00000000"
        return params


# The plt.show function will be overwriten to this.
# Modified from matplotlib_inline (BSD 3-Clause "New" or "Revised" License)
# https://github.com/ipython/matplotlib-inline
def show(close=True, block=None):
    logger = Logger.current_logger
    from matplotlib._pylab_helpers import Gcf

    try:
        for figure_manager in Gcf.get_all_fig_managers():
            logger.print_figure(figure_manager)
    finally:
        show._called = True
        if close and Gcf.get_all_fig_managers():
            plt.close("all")
