from __future__ import annotations
import sys
import logging
from contextlib import contextmanager
from qtpy import QtWidgets as QtW, QtGui, QtCore
from magicgui.backends._qtpy.widgets import QBaseWidget
from magicgui.widgets import Widget
import logging
from typing import TYPE_CHECKING, Any, Union, overload
from ..utils import rst_to_html

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
    from PIL import Image
    from pathlib import Path

# See https://stackoverflow.com/questions/28655198/best-way-to-display-logs-in-pyqt


class Output:
    TEXT = 0
    HTML = 1
    IMAGE = 2


Printable = Union[str, QtGui.QImage]


class QtLogger(QtW.QTextEdit):
    process = QtCore.Signal(tuple)

    def __init__(self, parent=None, max_history: int = 500):
        super().__init__(parent=parent)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)
        self._max_history = int(max_history)
        self._n_lines = 0
        self.process.connect(self.update)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        @self.customContextMenuRequested.connect
        def rightClickContextMenu(point):
            menu = self._make_contextmenu(point)
            if menu:
                menu.exec_(self.mapToGlobal(point))

    def update(self, output: tuple[int, Printable]):
        output_type, obj = output
        if output_type == Output.TEXT:
            self.moveCursor(QtGui.QTextCursor.End)
            self.insertPlainText(obj)
            self.moveCursor(QtGui.QTextCursor.End)
        elif output_type == Output.HTML:
            self.moveCursor(QtGui.QTextCursor.End)
            self.insertHtml(obj)
            self.moveCursor(QtGui.QTextCursor.End)
        elif output_type == Output.IMAGE:
            cursor = self.textCursor()
            cursor.insertImage(obj)
            self.insertPlainText("\n\n")
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        else:
            raise TypeError("Wrong type.")
        self._post_append()

    def appendText(self, text: str):
        """Append text in the main thread."""
        self.process.emit((Output.TEXT, text))

    def appendHtml(self, html: str):
        """Append HTML in the main thread."""
        self.process.emit((Output.HTML, html))

    def appendImage(self, qimage: QtGui.QImage):
        """Append image in the main thread."""
        self.process.emit((Output.IMAGE, qimage))

    def _post_append(self):
        """Check the history length."""
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

    # These methods below are modified from qtconsole.rich_jupyter_widget.py

    def _make_contextmenu(self, pos):
        """Reimplemented to return a custom context menu for images."""
        format = self.cursorForPosition(pos).charFormat()
        name = format.stringProperty(QtGui.QTextFormat.ImageName)
        if name:
            menu = QtW.QMenu(self)

            menu.addAction("Copy Image", lambda: self._copy_image(name))
            menu.addAction("Save Image As...", lambda: self._save_image(name))
            menu.addSeparator()
            return menu

    def _copy_image(self, name):
        image = self._get_image(name)
        QtW.QApplication.clipboard().setImage(image)

    def _save_image(self, name, format="PNG"):
        """Shows a save dialog for the ImageResource with 'name'."""
        dialog = QtW.QFileDialog(self, "Save Image")
        dialog.setAcceptMode(QtW.QFileDialog.AcceptSave)
        dialog.setDefaultSuffix(format.lower())
        dialog.setNameFilter(f"{format} file (*.{format.lower()})")
        if dialog.exec_():
            filename = dialog.selectedFiles()[0]
            image = self._get_image(name)
            image.save(filename, format)

    def _get_image(self, name):
        """Returns the QImage stored as the ImageResource with 'name'."""
        document = self.document()
        image = document.resource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(name))
        return image


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

        logging.getLogger(__name__).addHandler(logger)

    Inline plot in the widget

    .. code-block:: python

        with logger.set_plt():
            plt.plot(np.random.random(100))

    """

    current_logger: Logger | None = None

    def __init__(self):
        logging.Handler.__init__(self)
        Widget.__init__(
            self, widget_type=QBaseWidget, backend_kwargs={"qwidg": QtLogger}
        )

    def emit(self, record):
        msg = self.format(record)
        self.print(msg)

    def clear(self):
        """Clear all the histories."""
        self.native.clear()
        return None

    def print(self, *msg, sep=" ", end="\n"):
        """Print things in the end of the logger widget."""
        self.native.appendText(sep.join(map(str, msg)) + end)
        return None

    def print_html(self, html: str, end="<br></br>"):
        """Print things in the end of the logger widget using HTML string."""
        self.native.appendHtml(html + end)
        return None

    def print_rst(self, rst: str, end="\n"):
        """Print things in the end of the logger widget using rST string."""
        html = rst_to_html(rst, unescape=False)
        if end == "\n":
            end = "<br></br>"
        self.native.appendHtml(html + end)
        return None

    def print_table(
        self,
        table,
        header: bool = True,
        index: bool = True,
        precision: int | None = None,
    ):
        """
        Print object as a table in the logger widget.

        Parameters
        ----------
        table : table-like object
            Any object that can be passed to ``pandas.DataFrame`` can be used.
        header : bool, default is True
            Whether to show the header row.
        index : bool, default is True
            Whether to show the index column.
        precision: int, options
            If given, float value will be rounded by this parameter.
        """
        import pandas as pd

        df = pd.DataFrame(table)
        if precision is None:
            formatter = None
        else:
            formatter = lambda x: f"{x:.{precision}f}"
        self.native.appendHtml(
            df.to_html(header=header, index=index, float_format=formatter)
        )
        return None

    def print_image(
        self,
        arr: str | Path | np.ndarray | Image,
        vmin=None,
        vmax=None,
        cmap=None,
        norm=None,
        width=None,
        height=None,
    ) -> None:
        """Print an array as an image in the logger widget. Can be a path."""
        from magicgui import _mpl_image

        img = _mpl_image.Image()

        img.set_data(arr)
        img.set_clim(vmin, vmax)
        img.set_cmap(cmap)
        img.set_norm(norm)

        val = img.make_image()
        h, w, _ = val.shape
        image = QtGui.QImage(val, w, h, QtGui.QImage.Format_RGBA8888)

        # set scale of image
        if width is None and height is None:
            if w / 3 > h / 2:
                width = 360
            else:
                height = 240

        if width is None:
            image = image.scaledToHeight(height, QtCore.Qt.SmoothTransformation)
        else:
            image = image.scaledToWidth(width, QtCore.Qt.SmoothTransformation)

        self.native.appendImage(image)
        return None

    def print_figure(self, fig: Figure) -> None:
        """Print matplotlib Figure object like inline plot."""
        fig.canvas.draw()
        data = np.asarray(fig.canvas.renderer.buffer_rgba(), dtype=np.uint8)
        self.print_image(data)

        return None

    def write(self, msg) -> None:
        self.print(msg, end="")
        return None

    def flush(self):
        pass

    def close(self) -> None:
        # This method collides between magicgui.widgets.Widget and logging.Handler.
        # Since the close method in Widget is rarely used, here just call the latter.
        return logging.Handler.close(self)

    @contextmanager
    def set_stdout(self):
        """A context manager for printing things in this widget."""
        try:
            sys.stdout = self
            yield self
        finally:
            sys.stdout = sys.__stdout__

    @contextmanager
    def set_logger(self, name=None):
        """A context manager for logging things in this widget."""
        try:
            logging.getLogger(name).addHandler(self)
            yield self
        finally:
            logging.getLogger(name).removeHandler(self)

    @overload
    def set_plt(self, style: str | None) -> None:
        ...

    @overload
    def set_plt(self, rc_context: dict[str, Any]) -> None:
        ...

    @contextmanager
    def set_plt(self, style: str = None, rc_context: dict[str, Any] = {}):
        """A context manager for inline plot in the logger widget."""
        if not MATPLOTLIB_AVAILABLE:
            yield self
            return None
        self.__class__.current_logger = self

        if isinstance(style, dict):
            if rc_context:
                raise TypeError("style must be str.")
            rc_context = style
            style = None

        if style is None:
            style = self._get_proper_plt_style()

        backend = mpl.get_backend()
        show._called = False
        try:
            mpl.use("module://magicclass.widgets.logger")
            with plt.style.context(style), plt.rc_context(rc_context):
                yield self
        finally:
            if not show._called:
                show()
            self.__class__.current_logger = None
            mpl.use(backend)
        return None

    def _get_proper_plt_style(self) -> dict[str, Any]:
        color = self._widget._qwidget._get_background_color()[:3]
        is_dark = sum(color) < 382.5  # 255*3/2
        if is_dark:
            params = plt.style.library["dark_background"]
        else:
            keys = plt.style.library["dark_background"].keys()
            with plt.style.context("default"):
                params: dict[str, Any] = {}
                rcparams = plt.rcParams
                for key in keys:
                    params[key] = rcparams[key]
        bg = _tuple_to_color(color)
        params["figure.facecolor"] = bg
        params["axes.facecolor"] = bg
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


def _tuple_to_color(tup: tuple[int, int, int]):
    return "#" + "".join(hex(int(t))[2:] for t in tup)
