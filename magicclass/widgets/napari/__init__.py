try:
    import napari
    from .widgets import NapariCanvas
except ImportError:
    from ..utils import NotInstalled
    msg = "Module 'napari' is not installed. To use NapariCanvas, " \
          "you have to install it by:\n" \
          "   $ pip install napari[all]\n" \
          "or\n" \
          "   $ conda install napari -c conda-forge"
    NapariCanvas = NotInstalled(msg)

__all__ = ["NapariCanvas"]