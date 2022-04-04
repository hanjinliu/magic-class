"""
VTK (Visualization Toolkit) support in a magicgui/magic-class way.
This extension submodule depends on ``vedo``.

.. code-block:: shell

    pip install vedo

"""

from .widgets import VtkCanvas

__all__ = ["VtkCanvas"]
