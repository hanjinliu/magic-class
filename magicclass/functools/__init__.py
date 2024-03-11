"""
A magic-class submodule that mimics the built-in `functools` module.
"""

from ._dispatch import singledispatch, singledispatchmethod
from ._partial import partial, partialmethod
from ._wraps import wraps


__all__ = [
    "partial",
    "partialmethod",
    "singledispatch",
    "singledispatchmethod",
    "wraps",
]
