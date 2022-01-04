from __future__ import annotations
from typing import Callable, TYPE_CHECKING
from magicgui.widgets import FunctionGui

if TYPE_CHECKING:
    from ._base import BaseGui
    from .menu_gui import ContextMenuGui

def get_parameters(fgui: FunctionGui):
    return {k: v.default for k, v in fgui.__signature__.parameters.items()}

def define_callback(self: BaseGui, callback: Callable):
    *_, clsname, funcname = callback.__qualname__.split(".")
    def _callback():
        # search for parent instances that have the same name.
        current_self = self
        while not (hasattr(current_self, funcname) and 
                   current_self.__class__.__name__ == clsname):
            current_self = current_self.__magicclass_parent__
        getattr(current_self, funcname)()
        return None
    return _callback

def define_context_menu(contextmenu: ContextMenuGui, parent):
    def rightClickContextMenu(point):
        contextmenu.native.exec_(parent.mapToGlobal(point))
    return rightClickContextMenu

class MagicClassConstructionError(Exception):
    """
    This exception will be raised when class definition is not a valid magic-class.
    """    