from __future__ import annotations
from typing_extensions import get_args, get_origin
import inspect
from magicgui.type_map import type_matcher
from magicgui.types import WidgetTuple

from ._utils import is_subclass
from ..widgets import ListEdit


@type_matcher
def list_of_any(value, annotation) -> WidgetTuple | None:
    """Determine if value/annotation is list[...]."""
    if annotation and annotation is not inspect._empty:
        orig = get_origin(annotation)
        args = get_args(annotation)
        if not (inspect.isclass(orig) and args):
            return None
        if is_subclass(orig, list) or isinstance(orig, list):
            return ListEdit, {"annotation": args[0]}
    elif value:
        if isinstance(value, list) and len(set(type(v) for v in value)) == 1:
            return ListEdit, {"value": value}
    return None