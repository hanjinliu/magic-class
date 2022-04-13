from __future__ import annotations
import inspect
from typing import Any, TYPE_CHECKING, Iterable
import warnings
from docstring_parser import parse

if TYPE_CHECKING:
    from .._gui import BaseGui


def iter_members(cls: type, exclude_prefix: str = "__") -> Iterable[tuple[str, Any]]:
    """
    Iterate over all the members in the order of source code line number.
    This function is identical to inspect.getmembers except for the order
    of the results. We have to sort the name in the order of line number.
    """
    mro = (cls,) + inspect.getmro(cls)
    processed = set()
    names: list[str] = list(cls.__dict__.keys())
    try:
        for base in reversed(mro):
            for k in base.__dict__.keys():
                if k not in names:
                    names.append(k)

    except AttributeError:
        pass

    for key in names:
        try:
            value = getattr(cls, key)
            # handle the duplicate key
            if key in processed:
                raise AttributeError
        except AttributeError:
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            else:
                continue
        if not key.startswith(exclude_prefix):
            yield key, value
        processed.add(key)


def extract_tooltip(obj: Any) -> str:
    """Extract docstring for tooltip."""
    doc = parse(obj.__doc__)
    if doc.short_description is None:
        return ""
    elif doc.long_description is None:
        return doc.short_description
    else:
        return doc.short_description + "\n" + doc.long_description


def get_signature(func):
    """Similar to ``inspect.signature`` but safely returns ``Signature``."""
    if hasattr(func, "__signature__"):
        sig = func.__signature__
    else:
        sig = inspect.signature(func)
    return sig


def show_tree(ui: BaseGui) -> str:
    return _get_tree(ui)


def _get_tree(ui: BaseGui, depth: int = 0):
    pref = "\t" * depth
    children_str_list: list[str] = []
    for i, child in enumerate(ui.__magicclass_children__):
        text = _get_tree(child, depth=depth + 1)
        children_str_list.append(pref + f"\t{i:>3}: {text}")

    if children_str_list:
        children_str = "\n".join(children_str_list)
        out = f"'{ui.name}'\n{children_str}"
    else:
        out = f"'{ui.name}'"
    return out


def rst_to_html(rst: str, unescape: bool = True) -> str:
    """Convert rST string into HTML."""
    from docutils.examples import html_body

    try:
        body: bytes = html_body(rst, input_encoding="utf-8", output_encoding="utf-8")
        html = body.decode(encoding="utf-8")
        if unescape:
            from xml.sax.saxutils import unescape as _unescape

            html = _unescape(html)

    except Exception as e:
        warnings.warn(
            f"Could not convert string into HTML due to {type(e).__name__}: {e}",
            UserWarning,
        )
        html = rst
    return html
