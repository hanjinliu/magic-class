from __future__ import annotations
from typing import Callable

__all__ = [
    "napari_light_theme",
    "napari_dark_theme",
    "napari_system_theme",
]


class StyleSheet:
    def __init__(self, getter: Callable[[], str]):
        self.getter = getter

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.getter.__name__}>"

    def __str__(self) -> str:
        """Return style sheet."""
        return self.getter()

    def __add__(self, other: StyleSheet) -> StyleSheet:
        """Conjugate stylesheets."""

        def new_getter():
            s0 = self.getter()
            s1 = other.getter()
            return s0 + "\n" + s1

        return new_getter


def _napari_get_stylesheet(theme: str):
    # TODO: don't launch a viewer if possible.
    import napari

    viewer = napari.Viewer(show=False)
    viewer.theme = theme
    stylesheet = viewer.window._qt_window.styleSheet()
    viewer.close()
    return stylesheet


@StyleSheet
def napari_light_theme():
    return _napari_get_stylesheet("light")


@StyleSheet
def napari_dark_theme():
    return _napari_get_stylesheet("dark")


@StyleSheet
def napari_system_theme():
    return _napari_get_stylesheet("system")
