from __future__ import annotations
from ...gui._base import BaseGui
from ...gui import MenuGui, ToolBarGui, ClassGui
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import napari


def to_napari(
    magic_class: type[BaseGui] | None = None,
    *,
    viewer: napari.Viewer | None = None,
):
    """
    Send magic class to current napari viewer. Classes decorated with ``@magicclass``
    ``magicmenu`` and ``magictoolbar`` are supported.
    """

    def wrapper(cls: type[BaseGui]):
        if viewer is None:
            import napari

            _viewer = napari.current_viewer()
            if _viewer is None:
                _viewer = napari.Viewer()

        if not isinstance(cls, type):
            raise TypeError(f"Cannot decorate type {type(cls)}.")

        ui = cls()
        if issubclass(cls, ClassGui):
            _viewer.window.add_dock_widget(ui)
        elif issubclass(cls, MenuGui):
            _viewer.window.main_menu.addMenu(ui.native)
            ui.native.setParent(_viewer.window.main_menu, ui.native.windowFlags())
        elif issubclass(cls, ToolBarGui):
            _viewer.window._qt_window.addToolBar(ui.native)
        else:
            raise TypeError(
                f"Class {cls.__name__} is not a magic-class. Maybe you forgot decorating"
                "the class with '@magicclass'?"
            )
        _viewer.update_console({"ui": ui})
        return cls

    if magic_class is None:
        return wrapper
    else:
        return wrapper(magic_class)
