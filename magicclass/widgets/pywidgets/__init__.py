"""
This widget submodule contains "visible PyObject" widgets, which has similar
API as PyObject to operate items. They can be considered as a simpler form
of ``Table`` widget in ``magicgui``.
They are also equipped with custom delegate, contextmenu and double-click
callbacks.
"""

from .dict import DictWidget
from .list import ListWidget