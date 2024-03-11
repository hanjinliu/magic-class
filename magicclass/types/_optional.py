from __future__ import annotations
import typing
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    overload,
    TypeVar,
    get_args,
    get_origin,
)
from typing_extensions import Annotated
from magicclass.utils import is_type_like
from magicclass.signature import split_annotated_type, is_annotated

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
        if is_annotated(value):
            type0, opt0 = split_annotated_type(value)
            type_ = typing.Optional[type0]
            opt.update(annotation=type_, options=opt0)
            return Annotated[type_, opt]
        else:
            value_unwrapped = _unwrap_annotated(value)
            try:
                new_annot = typing.Optional[value]
            except TypeError:  # unhashable
                new_annot = _FakeOptional[value]
            opt.update(annotation=new_annot)
            return Annotated[value_unwrapped, opt]


def _unwrap_annotated(typ):
    origin = get_origin(typ)
    args = get_args(typ)
    if origin is Annotated:
        return args[0]
    if origin is not None and args:
        unwrapped = tuple(_unwrap_annotated(arg) for arg in args)
        return origin[unwrapped]
    return typ


class _FakeOptional(Generic[_T]):
    """This type is recognized as typing.Optional by OptionalWidget."""


if TYPE_CHECKING:
    from typing import Optional
else:

    class Optional(metaclass=_OptionalAlias):
        """
        Make Annotated type similar to `typing.Optional`.

        Arguments annotated with `Optional[int]` will create a `OptionalWidget` with a
        `SpinBox` as an inner widget.

        >>> from magicclass import magicclass, set_options
        >>> from magicclass.types import Optional

        >>> @magicclass
        >>> class A:
        ...     @set_options(a={"options": {"min": -1}})
        ...     def f(self, a: Optional[int]):
        ...         print(a)

        >>> ui = A()
        >>> ui.show()
        """

        def __new__(cls, *args, **kwargs):
            raise TypeError("Type Optional cannot be instantiated.")

        def __init_subclass__(cls, *args, **kwargs):
            raise TypeError(f"Cannot subclass {cls.__module__}.Optional.")
