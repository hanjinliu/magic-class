from __future__ import annotations
import typing
from typing import (
    TYPE_CHECKING,
    Any,
    overload,
    TypeVar,
)
from typing_extensions import Annotated, _AnnotatedAlias
from magicclass.utils import is_type_like
from magicclass.signature import split_annotated_type

_T = TypeVar("_T")


class _OptionalAlias(type):
    @overload
    def __getitem__(cls, value: type[_T]) -> type[typing.Optional[_T]]:
        ...

    @overload
    def __getitem__(
        cls, value: tuple[type[_T], dict[str, Any]]
    ) -> type[typing.Optional[_T]]:
        ...

    def __getitem__(cls, value):
        if not is_type_like(value):
            raise TypeError(
                "The first argument of Optional must be a type but "
                f"got {type(value)}."
            )
        from magicclass.widgets import OptionalWidget

        opt = dict(widget_type=OptionalWidget)
        if isinstance(value, _AnnotatedAlias):
            type0, opt0 = split_annotated_type(value)
            type_ = typing.Optional[type0]
            opt.update(annotation=type_, options=opt0)
            return Annotated[type_, opt]
        else:
            opt.update(annotation=typing.Optional[value])
            return Annotated[typing.Optional[value], opt]


if TYPE_CHECKING:
    from typing import Optional
else:

    class Optional(metaclass=_OptionalAlias):
        """
        Make Annotated type similar to ``typing.Optional``.

        Arguments annotated with ``Optional[int]`` will create a
        ``OptionalWidget`` with a ``SpinBox`` as an inner widget.

        >>> from magicclass import magicclass, set_options
        >>> from magicclass.types import Optional

        >>> @magicclass
        >>> class A:
        >>>     @set_options(a={"options": {"min": -1}})
        >>>     def f(self, a: Optional[int]):
        >>>         print(a)

        >>> ui = A()
        >>> ui.show()
        """

        def __new__(cls, *args, **kwargs):
            raise TypeError("Type Optional cannot be instantiated.")

        def __init_subclass__(cls, *args, **kwargs):
            raise TypeError(f"Cannot subclass {cls.__module__}.Optional.")
