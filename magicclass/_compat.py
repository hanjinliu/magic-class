from __future__ import annotations
from typing import TYPE_CHECKING
from magicgui.widgets.bases import ValueWidget, ContainerWidget

if TYPE_CHECKING:
    from typing import TypeGuard

try:
    from magicgui.widgets.bases import BaseValueWidget

    HAS_BASE_VALUE_WIDGET = True
except ImportError:
    HAS_BASE_VALUE_WIDGET = False

if HAS_BASE_VALUE_WIDGET:

    def is_value_widget(widget) -> TypeGuard[BaseValueWidget]:
        return isinstance(widget, BaseValueWidget)

    def has_changed_signal(widget) -> TypeGuard[BaseValueWidget | ContainerWidget]:
        return isinstance(widget, (BaseValueWidget, ContainerWidget))

else:

    def is_value_widget(widget) -> TypeGuard[ValueWidget | ContainerWidget]:
        return isinstance(widget, (ValueWidget, ContainerWidget))

    def has_changed_signal(widget) -> TypeGuard[ValueWidget | ContainerWidget]:
        return isinstance(widget, (ValueWidget, ContainerWidget))


__all__ = ["is_value_widget"]
