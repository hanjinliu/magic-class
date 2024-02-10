"""
This extension submodule depends on ``vedo``.

.. code-block:: shell

    pip install vedo

"""

from .widgets import VedoCanvas, VtkCanvas

__all__ = ["VedoCanvas", "VtkCanvas"]
