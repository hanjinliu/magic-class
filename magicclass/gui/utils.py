from __future__ import annotations
from typing import Any, Callable, TYPE_CHECKING, TypeVar
from magicgui.widgets import FunctionGui
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from ._base import BaseGui
    from .menu_gui import ContextMenuGui


def get_parameters(fgui: FunctionGui):
    return {k: v.default for k, v in fgui.__signature__.parameters.items()}


def define_callback(self: BaseGui, callback: Callable):
    """Define a callback function from a method."""
    *_, clsname, funcname = callback.__qualname__.split(".")
    mro = self.__class__.__mro__
    for base in mro:
        if base.__name__ == clsname:

            def _callback():
                with self.macro.blocked():
                    getattr(base, funcname)(self)
                return None

            break
    else:

        def _callback():
            # search for parent instances that have the same name.
            current_self = self
            while not (
                hasattr(current_self, funcname)
                and current_self.__class__.__name__ == clsname
            ):
                current_self = current_self.__magicclass_parent__
            with self.macro.blocked():
                getattr(current_self, funcname)()
            return None

    return _callback


def set_context_menu(contextmenu: ContextMenuGui, parent: BaseGui) -> None:
    parent.native.setContextMenuPolicy(Qt.CustomContextMenu)

    @parent.native.customContextMenuRequested.connect
    def rightClickContextMenu(point):
        contextmenu.native.exec_(parent.native.mapToGlobal(point))

    return None


_C = TypeVar("_C", bound=type)


def copy_class(cls: _C) -> _C:
    return type(cls.__name__, cls.__bases__, dict(cls.__dict__))


class MagicClassConstructionError(Exception):
    """
    This exception will be raised when class definition is not a valid magic-class.
    """


def format_error(
    e: Exception,
    hist: list[tuple[str, str, str]],
    name: str,
    attr: Any,
):
    hist_str = (
        "\n\t".join(map(lambda x: f"{x[0]} {x[1]} -> {x[2]}", hist))
        + f"\n\t\t{name} ({type(attr)}) <--- Error"
    )
    if not hist_str.startswith("\n\t"):
        hist_str = "\n\t" + hist_str
    if isinstance(e, MagicClassConstructionError):
        e.args = (f"\n{hist_str}\n{e}",)
        raise e
    else:
        raise MagicClassConstructionError(
            f"\n{hist_str}\n\n{type(e).__name__}: {e}"
        ) from e
