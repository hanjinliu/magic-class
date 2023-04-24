from __future__ import annotations
from abc import ABCMeta

import pathlib
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Sequence,
)
from typing_extensions import Annotated


if TYPE_CHECKING:
    from typing_extensions import Self


class _AnnotatedPathAlias(type):
    _file_edit_mode: str

    def __getitem__(cls, filter: str) -> Self:
        return Annotated[pathlib.Path, {"mode": cls._file_edit_mode, "filter": filter}]


class _AnnotatedPathAlias2(_AnnotatedPathAlias):
    def __instancecheck__(cls, instance: Any) -> bool:
        return isinstance(instance, pathlib.Path)

    def __subclasscheck__(cls, subclass: type) -> bool:
        return issubclass(subclass, pathlib.Path)


class _AnnotatedMultiPathAlias(ABCMeta):
    def __getitem__(cls, filter: str) -> Self:
        return Annotated[List[Path], {"mode": "rm", "filter": filter}]


class _Path(pathlib.Path, metaclass=_AnnotatedPathAlias):
    _file_edit_mode = "r"


class _SavePath(_Path):
    _file_edit_mode = "w"


class _DirPath(_Path):
    _file_edit_mode = "d"


class _MultiplePaths(Sequence[pathlib.Path], metaclass=_AnnotatedMultiPathAlias):
    pass


class Path(pathlib.Path, metaclass=_AnnotatedPathAlias2):
    """
    A subclass of ``pathlib.Path`` with additional type annotation variations.

    >>> Path  # identical to pathlib.Path for magicgui
    >>> Path.Read  # pathlib.Path with mode "r" (identical to Path)
    >>> Path.Save  # pathlib.Path with mode "w"
    >>> Path.Dir  # pathlib.Path with mode "d"
    >>> Path.Multiple  # pathlib.Path with mode "rm"
    >>> Path.Read["*.py"]  # pathlib.Path with mode "r" and filter "*.py"
    """

    _file_edit_mode = "r"

    Read = _Path
    Save = _SavePath
    Dir = _DirPath
    Multiple = _MultiplePaths

    def __new__(cls, *args, **kwargs):
        return pathlib.Path(*args, **kwargs)
