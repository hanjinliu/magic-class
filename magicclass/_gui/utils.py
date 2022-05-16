from __future__ import annotations
from typing import Any, TYPE_CHECKING, TypeVar
from magicgui.widgets import FunctionGui, _protocols, _bases, Widget
from magicgui.widgets._bases.value_widget import UNSET
from magicgui.type_map import get_widget_class
from magicgui.signature import magic_signature, MagicParameter, split_annotated_type
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from ._base import BaseGui
    from .menu_gui import ContextMenuGui


def get_parameters(fgui: FunctionGui):
    return {k: v.default for k, v in fgui.__signature__.parameters.items()}


def set_context_menu(contextmenu: ContextMenuGui, parent: BaseGui) -> None:
    parent.native.setContextMenuPolicy(Qt.CustomContextMenu)

    @parent.native.customContextMenuRequested.connect
    def rightClickContextMenu(point):
        contextmenu.native.exec_(parent.native.mapToGlobal(point))

    return None


_C = TypeVar("_C", bound=type)


def copy_class(cls: _C, ns: type) -> _C:
    out = type(cls.__name__, cls.__bases__, dict(cls.__dict__))
    out.__qualname__ = f"{ns.__qualname__}.{out.__name__}"
    return out


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


def callable_to_classes(f) -> list[type[Widget]]:
    sig = magic_signature(f)
    return [_parameter_to_widget_class(p) for p in sig.parameters.values()]


TZ_EMPTY = "__no__default__"


def _parameter_to_widget_class(param: MagicParameter):
    value = UNSET if param.default in (param.empty, TZ_EMPTY) else param.default
    annotation, options = split_annotated_type(param.annotation)
    options = options.copy()
    wdg_class, _ = get_widget_class(value, annotation, options)
    return wdg_class
