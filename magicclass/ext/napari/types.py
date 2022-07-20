from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Iterable, Tuple, List

# for now...
if TYPE_CHECKING:
    import pandas as pd

    Features = pd.DataFrame
    FeatureColumn = pd.Series
else:
    from typing import Protocol, Iterable

    class Features(Protocol):
        @property
        def columns(self) -> Iterable[str]:
            ...

    class FeatureColumn:
        pass


__all__ = ["Features", "FeatureColumn", "FeatureInfo"]


class _FeatureInfoAlias(type):
    def __getitem__(cls, names: str | tuple[str, ...]):
        if isinstance(names, str):
            names = (names,)
        else:
            for name in names:
                if not isinstance(name, str):
                    raise ValueError(
                        f"Cannot subscribe type {type(name)} to FeatureInfo."
                    )

        return Annotated[FeatureInfoInstance, {"column_choice_names": names}]


class FeatureInfo(metaclass=_FeatureInfoAlias):
    """
    A type representing a tuple of a DataFrame and its column names.

    .. code-block:: python

        def func(x: FeatureInfo["x", "y"]): ...

    Type annotation ``FeatureInfo["x", "y"]`` is essentially equivalent to
    ``tuple[pd.DataFrame, tuple[str, str]]``.
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Type {cls.__name__} cannot be instantiated.")


class FeatureInfoInstance(Tuple["pd.DataFrame", List[str]]):
    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Type {cls.__name__} cannot be instantiated.")
