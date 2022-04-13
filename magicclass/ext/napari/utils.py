from __future__ import annotations
import sys
from typing import Union, Callable, TYPE_CHECKING

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec
from functools import wraps
from ..._gui._base import BaseGui
from ..._gui import MenuGui, ToolBarGui, ClassGui
from napari.qt.threading import GeneratorWorker, FunctionWorker


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


Worker = Union[FunctionWorker, GeneratorWorker]

_P = ParamSpec("_P")


def process_worker(f: Callable[_P, Worker]) -> Callable[_P, None]:
    """
    Process returned worker of ``napari.qt.threading`` in a proper way.

    Open a progress bar and start worker in a parallel thread if function is called from GUI.
    Otherwise (if function is called from script), the worker will be executed as if the
    function is directly called. This function is useful in napari because when you are
    running workers in tandem the second one does not wait for the first one to finish, which
    causes inconsistency between operations on GUI and on Python interpreter.
    """

    @wraps(f)
    def wrapper(self: BaseGui, *args, **kwargs):
        worker: Worker = f(self, *args, **kwargs)
        if self[f.__name__].running:
            worker.start()
        else:
            worker.run()
        return None

    f.__annotations__["return"] = None
    if hasattr(f, "__signature__"):
        f.__signature__ = f.__signature__.replace(return_annotation=None)
    return wrapper
