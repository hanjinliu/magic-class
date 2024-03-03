"""
This extension submodule depends on `vedo`.

```sh
pip install vedo
```
"""

from .widgets import VedoCanvas

__all__ = ["VedoCanvas"]


def __getattr__(key: str):
    if key == "VtkCanvas":
        import warnings

        warnings.warn(
            "The VtkCanvas has been renamed to `VedoCanvas`.",
            DeprecationWarning,
            stacklevel=2,
        )
        return VedoCanvas
    raise AttributeError(f"module {__name__} has no attribute {key}")
