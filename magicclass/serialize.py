from __future__ import annotations

from typing import Any, TYPE_CHECKING, Callable
from magicgui.widgets import PushButton, Container
from magicgui.widgets.bases import Widget, ValueWidget, CategoricalWidget
from magicclass._gui import BaseGui, MenuGuiBase, ToolBarGui
from magicclass._gui.mgui_ext import WidgetAction, Action

if TYPE_CHECKING:
    SerializableWidget = Container | MenuGuiBase | ToolBarGui


def serialize(
    ui: SerializableWidget,
    *,
    skip_empty: bool = True,
    skip_null: bool = True,
    skip_if: Callable[[Any], bool] | None = None,
) -> dict[str, Any]:
    """
    Serialize the GUI.

    This function convert a magicgui Container or a magic-class object to a dict.
    All the child container widgets will be recursively serialized. If the input widget
    has `__magicclass_serialize__` method, `ui.__magicclass_serialize__()` will be
    called to serialize it.

    Parameters
    ----------
    ui : magicgui.Container or magicclass
        The GUI to be serialized.
    skip_empty : bool, default True
        If True, skip the container widgets serialized to empty dict.
    skip_null : bool, default True
        If True, skip the categorical widgets with null values, which happens when
        the choices are empty.
    skip_if : callable, optional
        If provided, the widget will be skipped if ``skip_if(widget.value)`` returns
        True. This is useful when you want to skip the widgets with certain values,
        such as None or ndarray.

    Examples
    --------
    >>> from magicclass.serialize import serialize
    >>> @magicgui
    >>> def func(x: int = 1, y: str = "t"):
    ...     pass
    >>> serialize(func)
    {'x': 1, 'y': 't'}
    """
    if hasattr(ui, "__magicclass_serialize__"):
        return ui.__magicclass_serialize__()

    def _serialize_value(widget: ValueWidget | WidgetAction):
        if _is_null_state(widget) and skip_null:
            return _missing
        _value = widget.value
        if skip_if is not None and skip_if(_value):
            return _missing
        return _value

    out: dict[str, Any] = {}
    processed: set[int] = set()
    if isinstance(ui, BaseGui):
        for child in ui.__magicclass_children__:
            if id(child) in processed:
                continue
            if _is_value_widget_like(child):
                if (_value := _serialize_value(child)) is not _missing:
                    out[child.name] = _value
            else:
                ser = serialize(child, skip_empty=skip_empty, skip_null=skip_null)
                if len(ser) > 0 or not skip_empty:
                    out[child.name] = ser
            processed.add(id(child))

    for widget in ui:
        if isinstance(widget, (PushButton, Action)) or id(widget) in processed:
            continue
        if _is_value_widget_like(widget):
            if (_value := _serialize_value(widget)) is not _missing:
                out[widget.name] = _value
        elif isinstance(widget, (Container, MenuGuiBase, ToolBarGui)):
            out[widget.name] = serialize(
                widget, skip_empty=skip_empty, skip_null=skip_null
            )
        elif isinstance(widget, WidgetAction) and widget.support_value:
            if (_value := _serialize_value(widget.widget)) is not _missing:
                out[widget.name] = _value
        processed.add(id(widget))
    return out


_missing = object()


def deserialize(
    ui: SerializableWidget,
    data: dict[str, Any],
    *,
    missing_ok: bool = True,
    record: bool = False,
    emit: bool = True,
) -> None:
    """
    Deserialize the GUI.

    This function uses the input dict to update magicgui Container or a magic-class
    object. If the input widget has `__magicclass_deserialize__` method, then
    `ui.__magicclass_deserialize__(data)` will be called to deserialize it.

    Parameters
    ----------
    ui : magicgui.Container or magicclass
        The GUI to be updated.
    data : dict
        The dict used to update the GUI.
    missing_ok : bool, default True
        If True, ignore the missing keys in the input dict.
    record : bool, default False
        If False, macro recording will be disabled.
    emit : bool, default True
        If True, emit the value changed signal.
    """
    if not record and isinstance(ui, BaseGui):
        with ui.macro.blocked():
            return deserialize(ui, data, missing_ok=missing_ok, record=True, emit=emit)

    if not emit:
        with ui.changed.blocked():
            return deserialize(
                ui, data, missing_ok=missing_ok, record=record, emit=True
            )

    if hasattr(ui, "__magicclass_deserialize__"):
        ui.__magicclass_deserialize__(data)
        return

    if isinstance(ui, BaseGui):
        for child in ui.__magicclass_children__:
            if (val := _dict_get(data, child.name, missing_ok)) is not _missing:
                if _is_value_widget_like(child):
                    child.value = val
                else:
                    deserialize(child, val)

    for widget in ui:
        if isinstance(widget, (PushButton, Action)):
            continue
        if _is_value_widget_like(widget):
            if (value := _dict_get(data, widget.name, missing_ok)) is not _missing:
                widget.value = value
        elif isinstance(widget, (Container, MenuGuiBase, ToolBarGui)):
            if (val := _dict_get(data, widget.name, missing_ok)) is not _missing:
                deserialize(widget, val)
        elif isinstance(widget, WidgetAction) and widget.support_value:
            if (value := _dict_get(data, widget.name, missing_ok)) is not _missing:
                widget.value = value

    return None


def _dict_get(data: dict[str, Any], key: str, missing_ok: bool) -> Any:
    """Get value from dict, if not found, return default."""
    out = data.get(key, _missing)
    if out is _missing and not missing_ok:
        raise KeyError(f"Key {key!r} not found in the input dict.")
    return out


def _is_value_widget_like(obj) -> bool:
    if isinstance(obj, ValueWidget):
        return True
    if isinstance(obj, WidgetAction):
        return obj.support_value
    if isinstance(value_property := getattr(type(obj), "value", None), property):
        # all the value-like containers should have both fget and fset.
        return value_property.fget is not None and value_property.fset is not None
    return False


def _contains_none(choices: list[Any]) -> bool:
    """Check if the choices contains None."""
    # Should not be `None in choices`, which raises exception if choices contains
    # a ndarray.
    if len(choices) == 0:
        return False
    return any(c is None for c in choices)


def _is_null_state(obj: Widget):
    return (
        isinstance(obj, CategoricalWidget)
        and obj.value is None
        and not _contains_none(obj.choices)
    )
