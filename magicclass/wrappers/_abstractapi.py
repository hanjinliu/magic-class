from __future__ import annotations
import inspect
from typing import Callable, TYPE_CHECKING
import functools
from magicclass._exceptions import AbstractAPIError

if TYPE_CHECKING:
    from typing import NoReturn
    from magicclass._gui import MagicTemplate
    from magicclass.fields import MagicField


class abstractapi(Callable):
    """
    Wrapper used for marking abstract APIs.

    This wrapper is intended to be used in combination with the `location=` argument of
    `@set_design`, `field` or `vfield`.

    Examples
    --------
    >>> @magicclass
    >>> class A:
    ...     @magicclass
    ...     class B:
    ...         @abstractapi  # mark as abstract
    ...         def f(self): ...
    ...         f = abstractapi()  # or like this
    ...     @B.wraps
    ...     def f(self, i: int):
    ...         print(i)  # do something
    """

    def __init__(
        self,
        func: Callable | None = None,
        *,
        location: type[MagicTemplate] | MagicField | None = None,
    ):
        if func is not None:
            if not callable(func) or isinstance(func, type):
                raise TypeError("abstractapi can only be used on functions and methods")

            self.__name__ = repr(func)
            functools.wraps(func)(self)
        else:
            self.__name__ = "unknown"
        self._resolved = False
        self._location = location
        if location is not None and not hasattr(self, "__signature__"):
            self.__signature__ = inspect.Signature([])

    def __call__(self, *args, **kwargs) -> NoReturn:
        raise AbstractAPIError(
            f"Function {self._get_qual_name()} is an abstract API so it cannot be "
            "called."
        )

    def __set_name__(self, owner: type, name: str):
        self.__name__ = name
        self.__qualname__ = f"{owner.__qualname__}.{name}"
        api = getattr(self._location, name, None)
        if isinstance(api, abstractapi):
            api.resolve()
            if not hasattr(self, "__signature__"):
                api.__signature__ = inspect.Signature([])

    def __get__(self, instance, owner=None) -> abstractapi:
        """Always return the same object."""
        return self

    def __repr__(self):
        return f"abstractapi<{self._get_qual_name()}, resolved={self._resolved}>"

    def _get_qual_name(self) -> str:
        return getattr(self, "__qualname__", self.__name__)

    def resolve(self) -> None:
        """Mark the API as solved."""
        self._resolved = True
        return None

    def check_resolved(self) -> None:
        """Check if the abstract API has been resolved by `wraps`."""
        if not self._resolved:
            raise AbstractAPIError(f"{self!r} is not redefined in the parent class.")
        return None

    def get_location(self) -> type[MagicTemplate] | None:
        loc = self._location
        if loc is None:
            return None

        from magicclass.fields import MagicField

        if isinstance(loc, MagicField):
            return loc.constructor
        return loc
