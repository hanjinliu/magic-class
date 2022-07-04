from __future__ import annotations
from functools import wraps

from typing import Any, Callable, Mapping, TYPE_CHECKING, TypeVar
from .signature import upgrade_signature

if TYPE_CHECKING:
    from ._gui import BaseGui

    F = TypeVar("F", bound=Callable)
    T = TypeVar("T", bound=BaseGui)


class MagicClassNamespace(Mapping[str, Callable]):
    def __init__(self, name: str | None = None) -> None:
        self._namespace: dict[int, dict[str, Callable]] = {}
        self._default_owner = None
        self._name = name or f"MagicClass{hex(id(self))}"

    def __set_name__(self, owner: type, name: str) -> None:
        self._default_owner = owner
        self._name = name

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj[self._name]

    def register(self, function: F, name: str | None = None) -> F:
        # wrap function
        if name is None:
            name = function.__name__
        self._namespace[name] = function
        return function

    def construct(
        self,
        owner: type[T] | None = None,
        base: type | None = None,
    ) -> T:
        if owner is None:
            if self._default_owner is None:
                raise ValueError("Namespace is not owned by a class.")
            owner = self._default_owner
        if base is None:
            from ._gui import ClassGui

            base = ClassGui

        ns: dict[str, Any] = {}

        for fname, function in self._namespace.items():
            ns[fname] = self.wrap_function(function, owner)

        cls = type(self._name, (base,), ns)
        return cls(name=self._name)

    def __getitem__(self, key: str) -> Callable:
        return self._namespace[key]

    def __len__(self) -> int:
        return len(self._namespace)

    def __iter__(self):
        return iter(self._namespace)

    @staticmethod
    def wrap_function(function, owner: type[T]):
        @wraps(function)
        def _func(bgui: T, *args, **kwargs):
            parent = bgui.find_ancestor(owner)
            return function(parent, *args, **kwargs)

        if hasattr(function, "__signature__"):
            _func.__signature__ = function.__signature__
        return _func


class MagicClassRegistry:
    def __init__(self):
        self._registry: dict[int, MagicClassNamespace] = {}

    def register(self, id: int, func: F | None = None, name: str | None = None):
        def _register(function: F) -> F:
            namespace = self._registry.get(id, None)
            if namespace is None:
                namespace = MagicClassNamespace()
                self._registry[id] = namespace

            namespace.register(function, name=name)
            return function

        return _register if func is None else _register(func)

    def construct(self, id: int, owner, base: type[T]) -> T:
        return self._registry[id].construct(owner=owner, base=base)
