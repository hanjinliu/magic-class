from __future__ import annotations

from typing import Any, Generic, TypeVar

_V = TypeVar("_V")

# name of the attribute of each instance that stores the per-instance caches
_STORE_NAME = "__magicclass_instance_cache__"
_MISSING = object()


class InstanceCache(Generic[_V]):
    """A mapping from instances to values, stored in the instances themselves.

    Descriptors (fields, thread workers, etc.) are class attributes, so they need
    a place to store the objects created for each instance. Storing them in a dict
    keyed by `id(instance)` keeps all the objects (and the instances referred by
    them) alive forever, and the cached value of a deleted instance may be returned
    for a new instance that happens to have the same ID. `WeakKeyDictionary` does
    not work either, because cached values usually refer to the instance.

    This class stores the values in the `__dict__` of each instance, so that the
    values are released together with the instance (reference cycles are collected
    by the garbage collector). Objects without `__dict__` fall back to a dict keyed
    by the ID.
    """

    def __init__(self) -> None:
        self._fallback: dict[int, _V] = {}

    def _get_store(self, obj: Any, create: bool) -> dict[InstanceCache, Any] | None:
        try:
            ns = object.__getattribute__(obj, "__dict__")
        except (AttributeError, TypeError):
            return None
        if not isinstance(ns, dict):  # e.g. mappingproxy
            return None
        if (store := ns.get(_STORE_NAME)) is None and create:
            store = ns[_STORE_NAME] = {}
        return store

    def get(self, obj: Any, default: Any = None) -> _V | Any:
        if (store := self._get_store(obj, create=False)) is None:
            return self._fallback.get(id(obj), default)
        return store.get(self, default)

    def __getitem__(self, obj: Any) -> _V:
        if (value := self.get(obj, _MISSING)) is _MISSING:
            raise KeyError(obj)
        return value

    def __setitem__(self, obj: Any, value: _V) -> None:
        if (store := self._get_store(obj, create=True)) is None:
            self._fallback[id(obj)] = value
        else:
            store[self] = value

    def __contains__(self, obj: Any) -> bool:
        return self.get(obj, _MISSING) is not _MISSING

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
