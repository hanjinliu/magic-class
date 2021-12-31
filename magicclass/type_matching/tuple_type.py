from __future__ import annotations
from typing_extensions import get_args, get_origin
import inspect
from magicgui.type_map import type_matcher
from magicgui.types import WidgetTuple

from ._utils import is_subclass
from ..widgets import TupleEdit


@type_matcher
def tuple_of_any(value, annotation) -> WidgetTuple | None:
    """Determine if value/annotation is tuple[...]."""
    if annotation and annotation is not inspect._empty:
        orig = get_origin(annotation)
        args = get_args(annotation)
        if not (inspect.isclass(orig) and args):
            return None
        if is_subclass(orig, tuple) or isinstance(orig, tuple):
            return TupleEdit, {"annotation": annotation}
    elif value:
        if isinstance(value, tuple):
            return TupleEdit, {"value": value}
    return None