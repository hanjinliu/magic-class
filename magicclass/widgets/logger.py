from __future__ import annotations
import sys
import logging
from pathlib import Path
from contextlib import contextmanager, suppress

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal
from magicgui.backends._qtpy.widgets import QBaseWidget
from magicgui.widgets import Widget
import logging
from typing import TYPE_CHECKING, Any, Union, overload, NamedTuple

from magicclass.utils import rst_to_html

if TYPE_CHECKING:
    import numpy as np
    from matplotlib.figure import Figure as mpl_Figure
    from matplotlib.backend_bases import FigureManagerBase, RendererBase


# See https://stackoverflow.com/questions/28655198/best-way-to-display-logs-in-pyqt


# Variable "FigureCanvas" should globally updated to plot figure inside the logger
# However, importing FigureCanvasAgg should be done lazily. Here's how to hack
# this procedure.
class FigureCanvasType:
    def __init__(self):
        self._canvas_type = None

    @property
    def FigureCanvasAgg(self):
        if self._canvas_type is None:
            from matplotlib.backends.backend_agg import FigureCanvasAgg

            self._canvas_type = FigureCanvasAgg
        return self._canvas_type

    def __getattr__(self, name):
        return getattr(self.FigureCanvasAgg, name)

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.FigureCanvasAgg(*args, **kwds)


FigureCanvas = FigureCanvasType()


class Output:
    """Logger output types."""

    TEXT = 0
    HTML = 1
    IMAGE = 2
    LINK = 3


class linkedStr(NamedTuple):
    text: str
    link: str


Printable = Union[str, QtGui.QImage, linkedStr]
# HREF_PATTERN = re.compile(r"<a href=.+>.+</a>")


class QFinderWidget(QtW.QDialog):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent, Qt.WindowType.SubWindow)
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(_layout)
        _line = QtW.QLineEdit()
        _btn_prev = QtW.QPushButton("▲")
        _btn_next = QtW.QPushButton("▼")
        _btn_prev.setFixedSize(18, 18)
        _btn_next.setFixedSize(18, 18)
        _layout.addWidget(_line)
        _layout.addWidget(_btn_prev)
        _layout.addWidget(_btn_next)
        _btn_prev.clicked.connect(self._find_prev)
        _btn_next.clicked.connect(self._find_next)
        _line.textChanged.connect(self._find_next)
        self._line_edit = _line

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> QtLogger: ...
    # fmt: on

    def lineEdit(self) -> QtW.QLineEdit:
        return self._line_edit

    def _find_prev(self):
        text = self._line_edit.text()
        if text == "":
            return
        qlogger = self.parentWidget()
        flag = QtGui.QTextDocument.FindFlag.FindBackward
        found = qlogger.find(text, flag)
        if not found:
            qlogger.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            qlogger.find(text, flag)

    def _find_next(self):
        text = self._line_edit.text()
        if text == "":
            return
        qlogger = self.parentWidget()
        found = qlogger.find(text)
        if not found:
            qlogger.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
            qlogger.find(text)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == Qt.Key.Key_Escape:
            self.hide()
            self.parentWidget().setFocus()
        elif a0.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if a0.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._find_prev()
            else:
                self._find_next()
        return super().keyPressEvent(a0)


class QtLogger(QtW.QTextEdit):
    process = Signal(tuple)

    def __init__(self, parent=None, max_history: int = 500):
        super().__init__(parent=parent)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self._max_history = int(max_history)
        self._n_lines = 0
        self.process.connect(self.update)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        @self.customContextMenuRequested.connect
        def rightClickContextMenu(point):
            menu = self._make_contextmenu(point)
            if menu:
                menu.exec_(self.mapToGlobal(point))

        self._last_save_path = None
        self._finder_widget = None
        self._anchor = None

    def update(self, output: tuple[int, Printable]):
        output_type, obj = output
        if output_type == Output.TEXT:
            self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            self.insertPlainText(obj)
            self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        elif output_type == Output.HTML:
            self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            self.insertHtml(obj)
            self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        elif output_type == Output.IMAGE:
            cursor = self.textCursor()
            cursor.insertImage(obj)
            self.insertPlainText("\n\n")
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        elif output_type == Output.LINK:
            linkedstr = linkedStr(*obj)
            cursor = self.textCursor()
            linkFormat = cursor.charFormat()
            linkFormat.setAnchor(True)
            linkFormat.setAnchorHref(linkedstr.link)
            linkFormat.setFontUnderline(True)
            linkFormat.setForeground(QtGui.QBrush(QtGui.QColor("blue")))
            cursor.insertText(linkedstr.text, linkFormat)
        else:
            raise TypeError("Wrong type.")
        self._post_append()
        return None

    def appendText(self, text: str):
        """Append text in the main thread."""
        self._emit_output(Output.TEXT, text)

    def appendHtml(self, html: str):
        """Append HTML in the main thread."""
        self._emit_output(Output.HTML, html)

    def appendImage(self, qimage: QtGui.QImage):
        """Append image in the main thread."""
        self._emit_output(Output.IMAGE, qimage)

    def appendHref(self, text: str, link: str):
        """Append link in the main thread."""
        self._emit_output(Output.LINK, linkedStr(text, link))

    def _emit_output(self, output: int, obj: Printable):
        with suppress(RuntimeError):
            self.process.emit((output, obj))

    def _post_append(self):
        """Check the history length."""
        if self._n_lines < self._max_history:
            self._n_lines += 1
            return None
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Down)
        cursor.deletePreviousChar()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        return None

    def _get_background_color(self) -> tuple[int, int, int, int]:
        return self.palette().color(self.backgroundRole()).getRgb()

    # These methods below are modified from qtconsole.rich_jupyter_widget.py

    def _make_contextmenu(self, pos):
        """Reimplemented to return a custom context menu for images."""
        format = self.cursorForPosition(pos).charFormat()
        menu = QtW.QMenu(self)
        menu.addAction("Find ...", self._find_string)
        menu.addAction("Export as HTML", self._export_as_html)
        menu.addSeparator()
        if name := format.stringProperty(QtGui.QTextFormat.Property.ImageName):
            menu.addAction("Copy Image", lambda: self._copy_image(name))
            menu.addAction("Save Image As...", lambda: self._save_image(name))
        return menu

    def _copy_image(self, name):
        image = self._get_image(name)
        if image is None:
            raise ValueError("Image not found")
        return QtW.QApplication.clipboard().setImage(image)

    def _save_image(self, name, format="PNG"):
        """Shows a save dialog for the ImageResource with 'name'."""
        image = self._get_image(name)
        if image is None:
            raise ValueError("Image not found")
        dialog = QtW.QFileDialog(self, "Save Image")
        dialog.setAcceptMode(QtW.QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix(format.lower())
        if self._last_save_path is None:
            self._last_save_path = Path.cwd()
        dialog.setDirectory(str(self._last_save_path))
        dialog.setNameFilter(f"{format} file (*.{format.lower()})")
        if dialog.exec_():
            filename = dialog.selectedFiles()[0]
            image.save(filename, format)
            self._last_save_path = Path(filename).parent
        return None

    def _find_string(self):
        if self._finder_widget is None:
            self._finder_widget = QFinderWidget(self)
        self._finder_widget.show()
        self._finder_widget.lineEdit().setFocus()
        self._align_finder()

    def resizeEvent(self, event):
        if self._finder_widget is not None:
            self._align_finder()
        super().resizeEvent(event)

    def _align_finder(self):
        if fd := self._finder_widget:
            vbar = self.verticalScrollBar()
            if vbar.isVisible():
                fd.move(self.width() - fd.width() - vbar.width() - 3, 5)
            else:
                fd.move(self.width() - fd.width() - 3, 5)

    def _export_as_html(self):
        from ._html import HtmlExporter

        HtmlExporter(self).export()

    def _get_image(self, name):
        """Returns the QImage stored as the ImageResource with 'name'."""
        document = self.document()
        image = document.resource(
            QtGui.QTextDocument.ResourceType.ImageResource, QtCore.QUrl(name)
        )
        return image

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        self._anchor = self.anchorAt(e.pos())
        self.viewport().setCursor(
            Qt.CursorShape.PointingHandCursor
            if self._anchor
            else Qt.CursorShape.IBeamCursor
        )
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(e)
        _anchor = self.anchorAt(e.pos())
        self.viewport().setCursor(
            Qt.CursorShape.PointingHandCursor if _anchor else Qt.CursorShape.IBeamCursor
        )
        return super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            _anchor = self.anchorAt(e.pos())
            if self._anchor == _anchor:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._anchor))
            self._anchor = None
        return super().mouseReleaseEvent(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        mod = e.modifiers()
        if mod == Qt.KeyboardModifier.ControlModifier:
            if e.key() == Qt.Key.Key_F:
                self._find_string()
                return None
        return super().keyPressEvent(e)


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
        self.native: QtLogger

    def emit(self, record):
        """Handle the logging event."""
        msg = self.format(record)
        self.print(msg)
        return None

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
        arr: str | Path | np.ndarray,
        vmin=None,
        vmax=None,
        cmap=None,
        norm=None,
        width=None,
        height=None,
    ) -> None:
        """Print an array as an image in the logger widget. Can be a path."""
        from magicgui.widgets._image import _mpl_image

        img = _mpl_image.Image()

        img.set_data(arr)
        img.set_clim(vmin, vmax)
        img.set_cmap(cmap)
        img.set_norm(norm)

        val = img.make_image()
        h, w, _ = val.shape
        image = QtGui.QImage(val, w, h, QtGui.QImage.Format.Format_RGBA8888)

        # set scale of image
        if width is None and height is None:
            if w / 3 > h / 2:
                width = 360
            else:
                height = 240

        if width is None:
            image = image.scaledToHeight(
                height, Qt.TransformationMode.SmoothTransformation
            )
        else:
            image = image.scaledToWidth(
                width, Qt.TransformationMode.SmoothTransformation
            )

        self.native.appendImage(image)
        return None

    def print_link(self, text: str, href: str):
        """Print a link in the logger widget."""
        self.native.appendHref(text, href)
        return None

    def print_figure(self, fig: mpl_Figure | FigureManagerBase) -> None:
        """Print matplotlib Figure object like inline plot."""
        import numpy as np

        fig.canvas.draw()
        data = np.asarray(fig.canvas.renderer.buffer_rgba(), dtype=np.uint8)
        self.print_image(data)
        return None

    def write(self, msg) -> None:
        """Handle the print event."""
        self.print(msg, end="")
        return None

    def flush(self):
        """Do nothing."""

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
    def set_logger(self, name=None, clear: bool = True):
        """A context manager for logging things in this widget."""
        logger = logging.getLogger(name)
        current_handler = logger.handlers
        try:
            if clear:
                for hd in current_handler:
                    logger.removeHandler(hd)
            logger.addHandler(self)
            yield self
        finally:
            logger.removeHandler(self)
            if clear:
                for hd in current_handler:
                    logger.addHandler(hd)

    @overload
    def set_plt(self, style: str | None) -> None:
        ...

    @overload
    def set_plt(self, rc_context: dict[str, Any]) -> None:
        ...

    @contextmanager
    def set_plt(self, style: str = None, rc_context: dict[str, Any] = {}):
        """A context manager for inline plot in the logger widget."""
        try:
            import matplotlib as mpl
            import matplotlib.pyplot as plt
        except ImportError:
            yield self
            return None
        self.__class__.current_logger = self

        if isinstance(style, dict):
            if rc_context:
                raise TypeError("style must be str.")
            rc_context = style
            style = None

        if style is None:
            try:
                style = self._get_proper_plt_style()
            except RuntimeError:
                style = "default"

        if "figure.dpi" not in rc_context:
            rc_context["figure.dpi"] = 800
        if "figure.figsize" not in rc_context:
            rc_context["figure.figsize"] = (4, 3)
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
            plt.close("all")
            mpl.use(backend)
        return None

    def _get_proper_plt_style(self) -> dict[str, Any]:
        import matplotlib.pyplot as plt

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
    import matplotlib.pyplot as plt
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
