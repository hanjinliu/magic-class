from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar, Union, overload, Any
from typing_extensions import Literal

from ._gui.menu_gui import ContextMenuGui, MenuGui
from ._gui.toolbar import ToolBarGui
from ._gui.class_gui import ClassGuiBase
from ._gui._base import PopUpMode, ErrorMode, MagicTemplate

if TYPE_CHECKING:
    from .types import WidgetType, WidgetTypeStr, PopUpModeStr, ErrorModeStr
    from ._gui._function_gui import FunctionGuiPlus
    from .stylesheets import StyleSheet
    from qtpy.QtWidgets import QWidget
    from .help import HelpWidget

Layout = Union[Literal["vertical"], Literal["horizontal"]]

_C = TypeVar("_C", bound=type)
_V = TypeVar("_V")

def build_help(ui: MagicTemplate, parent: QWidget | None = None) -> "HelpWidget": ...
def get_function_gui(ui: MagicTemplate, name: str) -> FunctionGuiPlus: ...
@overload
def magicclass(
    class_: _C,
    *,
    layout: Layout = "vertical",
    labels: bool = True,
    name: str | None = None,
    visible: bool | None = None,
    close_on_run: bool | None = None,
    popup_mode: PopUpModeStr | PopUpMode | None = None,
    error_mode: ErrorModeStr | ErrorMode | None = None,
    widget_type: WidgetTypeStr | WidgetType = WidgetType.none,
    icon_path: str | None = None,
    stylesheet: str | StyleSheet | None = None,
    parent=None,
) -> type[ClassGuiBase] | _C: ...
@overload
def magicclass(
    *,
    layout: Layout = "vertical",
    labels: bool = True,
    name: str | None = None,
    visible: bool | None = None,
    close_on_run: bool | None = None,
    popup_mode: PopUpModeStr | PopUpMode | None = None,
    error_mode: ErrorModeStr | ErrorMode | None = None,
    widget_type: WidgetTypeStr | WidgetType = WidgetType.none,
    icon_path: str | None = None,
    stylesheet: str | StyleSheet | None = None,
    parent=None,
) -> Callable[[_C], type[ClassGuiBase] | _C]: ...
@overload
def magicmenu(
    class_: _C,
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon_path: str | None = None,
    parent=None,
) -> type[MenuGui] | _C: ...
@overload
def magicmenu(
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon_path: str | None = None,
    parent=None,
) -> Callable[[_C], type[MenuGui] | _C]: ...
@overload
def magiccontext(
    class_: _C,
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon_path: str | None = None,
    parent=None,
) -> type[ContextMenuGui] | _C: ...
@overload
def magiccontext(
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon_path: str | None = None,
    parent=None,
) -> Callable[[_C], type[ContextMenuGui] | _C]: ...
@overload
def magictoolbar(
    class_: _C,
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon_path: str | None = None,
    parent=None,
) -> type[ToolBarGui] | _C: ...
@overload
def magictoolbar(
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon_path: str | None = None,
    parent=None,
) -> Callable[[_C], type[ToolBarGui] | _C]: ...
def redo(ui: MagicTemplate, index: int = -1) -> None: ...

class Parameters:
    def __init__(self): ...
    def __call__(self, *args: Any) -> None: ...
    def as_dict(self) -> dict[str, Any]: ...
