from __future__ import annotations
from typing import Coroutine, Awaitable, TypeVar, Any
import time
from qtpy.QtWidgets import QApplication

_T = TypeVar("_T")

# modified from https://github.com/nicoddemus/qt-async-threads


def _start_coroutine(coroutine: Coroutine) -> None:
    try:
        value = coroutine.send(None)
        if isinstance(value, Awaitable):
            value.coroutine = coroutine
            return
        else:
            assert False, f"Unexpected awaitable type: {value!r} {value}"
    except StopIteration:
        pass


def run_coroutine(coroutine: Coroutine[Any, Any, _T]) -> _T:
    """Run the coroutine and monitor it."""
    result: _T | None = None
    exception: Exception | None = None
    completed = False

    async def wrapper() -> None:
        nonlocal result, exception, completed
        try:
            result = await coroutine
        except Exception as e:
            exception = e
        completed = True

    _start_coroutine(wrapper())
    while not completed:
        # Must process events, otherwise GUI breaks.
        QApplication.processEvents()
        time.sleep(0.015)

    if exception is not None:
        raise exception
    return result
