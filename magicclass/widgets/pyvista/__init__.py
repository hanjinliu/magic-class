try:
    from .widgets import PyVistaCanvas
except ImportError:
    from ..utils import NotInstalled
    msg = "Module 'pyvistaqt' is not installed. To use PyVistaCanvas, " \
          "you have to install it by:\n" \
          "   $ pip install pyvistaqt"
    PyVistaCanvas = NotInstalled(msg)

__all__ = ["PyVistaCanvas"]