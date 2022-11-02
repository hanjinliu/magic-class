from __future__ import annotations
import logging
from functools import wraps
from ..widgets import Logger

_LOGGERS: dict[str, Logger] = {}

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
NOTSET = logging.NOTSET


@wraps(logging.getLogger)
def getLogger(name=None, show: bool = True):
    logger = logging.getLogger(name)
    if (handler := _LOGGERS.get(name, None)) is None:
        handler = _LOGGERS[name] = Logger()
        logger.addHandler(handler)
    if show:
        handler.show()
    return logger


def get_logger_widget(name=None) -> Logger:
    """Get the logger widget for the given logger name."""
    return _LOGGERS.get(name, None)


@wraps(logging.debug)
def debug(msg, *args, **kwargs):
    return getLogger().debug(msg, *args, **kwargs)


@wraps(logging.info)
def info(msg, *args, **kwargs):
    return getLogger().info(msg, *args, **kwargs)


@wraps(logging.warning)
def warning(msg, *args, **kwargs):
    return getLogger().warning(msg, *args, **kwargs)


@wraps(logging.error)
def error(msg, *args, **kwargs):
    return getLogger().error(msg, *args, **kwargs)


@wraps(logging.fatal)
def fatal(msg, *args, **kwargs):
    return getLogger().fatal(msg, *args, **kwargs)


@wraps(logging.critical)
def critical(msg, *args, **kwargs):
    return getLogger().critical(msg, *args, **kwargs)
