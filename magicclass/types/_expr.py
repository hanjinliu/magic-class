from __future__ import annotations

from typing import Any
from typing_extensions import Annotated


# Expression string
class _ExprInMeta(type):
    def __getitem__(cls, ns: dict[str, Any]) -> type[ExprStr]:
        if not isinstance(ns, dict):
            raise TypeError("namespace must be a dict")
        return Annotated[ExprStr, {"namespace": ns}]


class _ExprIn(metaclass=_ExprInMeta):
    def __new__(cls, *args, **kwargs):
        raise TypeError("ExprStr.In cannot be instantiated")


class ExprStr(str):
    """
    An expression string.

    `ExprStr` is a subclass of str that will be considered as an evaluation expression.
    `magicgui` interpret this type as a `EvalLineEdit`.

    >>> @magicgui
    >>> def func(x: ExprStr): ...

    >>> import numpy as np
    >>> @magicgui
    >>> def func(x: ExprStr.In[{"np": np}]): ...  # with given dict as namespace
    """

    In = _ExprIn

    def __new__(cls, x, ns: dict[str, Any] | None = None):
        self = str.__new__(cls, x)
        self.__ns = ns or {}
        return self

    def eval(self):
        """Evaluate the expression string."""
        return eval(str(self), self.__ns, {})
