from __future__ import annotations

import typing
from typing import (
    TYPE_CHECKING,
    Any,
    overload,
    TypeVar,
)
from typing_extensions import Annotated

_T = TypeVar("_T")
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")


class _UnionAlias(type):
    @overload
    def __getitem__(cls, value: tuple[_T, _T1]) -> typing.Union[_T, _T1]:
        ...

    @overload
    def __getitem__(cls, value: tuple[_T, _T1, _T2]) -> typing.Union[_T, _T1, _T2]:
        ...

    @overload
    def __getitem__(
        cls, value: tuple[_T, _T1, _T2, _T3]
    ) -> typing.Union[_T, _T1, _T2, _T3]:
        ...

    def __getitem__(cls, value):
        from magicclass.widgets import UnionWidget

        annotations = []
        opt = dict(widget_type=UnionWidget, nullable=False, annotations=annotations)
        if isinstance(value, tuple):
            for val in value:
                if val is not None:
                    annotations.append(val)
                else:
                    opt["nullable"] = True
        else:
            raise TypeError("Union must be a tuple or a dict.")
        # union = Union[tuple(annotations)]  # type: ignore
        return Annotated[Any, opt]


if TYPE_CHECKING:
    from typing import Union
else:

    class Union(metaclass=_UnionAlias):
        """
        Make Annotated type similar to `typing.Union`.

        Arguments annotated with `Union[int, str]` will create a `UnionWidget` with a
        `SpinBox` and a `LineEdit` as inner widgets.

        >>> from magicclass import magicclass
        >>> from magicclass.types import Union

        >>> @magicclass
        >>> class A:
        ...     def f(self, a: Union[int, str]):
        ...         print(a)

        >>> ui = A()
        >>> ui.show()
        """

        def __new__(cls, *args, **kwargs):
            raise TypeError("Type Union cannot be instantiated.")

        def __init_subclass__(cls, *args, **kwargs):
            raise TypeError(f"Cannot subclass {cls.__module__}.Union.")
