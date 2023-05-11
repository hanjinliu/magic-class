from __future__ import annotations
import logging
from typing import Any

from qtpy.sip import isdeleted
from magicclass.widgets import Logger

# The global logger widgets
_LOGGER_WIDGETS: dict[str, Logger] = {}


class MagicClassLogger(logging.Logger):
    """A magicclass widget-bound logger."""

    def __init__(self, widget: Logger, name: str, level=logging.NOTSET):
        super().__init__(name, level)
        self._widget = widget

    @property
    def widget(self) -> Logger:
        """The magicclass logger widget"""
        return self._widget

    def print(self, msg, sep=" ", end="\n"):
        """Print things in the end of the logger widget."""
        self._widget.print(msg, sep=sep, end=end)

    def print_html(self, msg: str, end="<br></br>"):
        """Print things in the end of the logger widget using HTML string."""
        self._widget.print_html(msg, end=end)

    def print_rst(self, rst: str, end="\n"):
        """Print things in the end of the logger widget using rST string."""
        self._widget.print_rst(rst, end=end)

    def print_table(
        self,
        table: Any,
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
        self._widget.print_table(table, header=header, index=index, precision=precision)

    def print_image(
        self,
        arr,
        vmin=None,
        vmax=None,
        cmap=None,
        norm=None,
        width=None,
        height=None,
    ) -> None:
        """Print an array as an image in the logger widget. Can be a path."""
        self._widget.print_image(
            arr, vmin=vmin, vmax=vmax, cmap=cmap, norm=norm, width=width, height=height
        )

    def print_figure(self, fig):
        """Print matplotlib Figure object like inline plot."""
        self._widget.print_figure(fig)

    def print_link(self, text: str, href: str):
        """Print a hypter link in the logger widget."""
        self._widget.print_link(text, href)

    def set_stdout(self):
        """A context manager for printing things in this widget."""
        return self._widget.set_stdout()

    def set_logger(self, clear: bool = True):
        """A context manager for logging things in this widget."""
        return self._widget.set_logger(self.name, clear=clear)

    def set_plt(self, style: str = None, rc_context: dict[str, Any] = {}):
        """A context manager for inline plot in the logger widget."""
        return self._widget.set_plt(style=style, rc_context=rc_context)

    def setLevel(self, level) -> None:
        """Set the logging level of this logger."""
        super().setLevel(level)
        logging.getLogger(self.name).setLevel(level)  # must set the root logger level


def getLogger(name: str | None = None, show: bool = False) -> MagicClassLogger:
    """
    Get a magicclass logger.

    The returned logger has a name specific logger widget. Many method of
    ``magicclass.widgets.Logger`` are also available.

    >>> from magicclass import logging
    >>> logger = logging.getLogger("your-app-name")
    >>> logger.widget.show()  # show the logger widget
    >>> logger.setLevel(logging.DEBUG)  # set the logging level
    >>> logger.debug("debug message")  # log a debug message
    >>> # widget is also a handler
    >>> logger.widget.setFormatter(
    ...     logging.Formatter(fmt="%(levelname)s || %(message)s")
    ... )

    """
    logger = logging.getLogger(name)
    if (handler := _LOGGER_WIDGETS.get(name, None)) is None:
        handler = _LOGGER_WIDGETS[name] = Logger()
        logger.addHandler(handler)
    elif isdeleted(handler.native):
        handler = _LOGGER_WIDGETS[name] = Logger()
        logger.addHandler(handler)
    if show:
        handler.show()
    return MagicClassLogger(handler, logger.name, logger.level)


def debug(msg, *args, **kwargs):
    return getLogger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    return getLogger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    return getLogger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    return getLogger().error(msg, *args, **kwargs)


def fatal(msg, *args, **kwargs):
    return getLogger().fatal(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    return getLogger().critical(msg, *args, **kwargs)
