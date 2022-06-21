from __future__ import annotations
from typing import Any, TYPE_CHECKING
import weakref
from qtpy.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout
from magicgui.widgets import Widget, _protocols
from magicgui.widgets._bases import ValueWidget, RangedWidget
from magicgui.widgets._concrete import merge_super_sigs as _merge_super_sigs
from magicgui.backends._qtpy.widgets import QBaseWidget

if TYPE_CHECKING:
    from .._gui import BaseGui, ContextMenuGui


class _NotInitialized:
    """This class helps better error handling."""

    def __init__(self, msg: str):
        self.msg = msg

    def __getattr__(self, key: str):
        raise RuntimeError(self.msg)


class FreeWidget(Widget):
    """A Widget class with any QWidget as a child."""

    _widget = _NotInitialized(
        "Widget is not correctly initialized. Must call `super().__init__` before using "
        "the widget."
    )

    def __init__(self, layout="vertical", **kwargs):
        super().__init__(
            widget_type=QBaseWidget, backend_kwargs={"qwidg": QWidget}, **kwargs
        )
        self.native: QWidget
        self.central_widget: QWidget | None = None
        if layout == "vertical":
            self.native.setLayout(QVBoxLayout())
        elif layout == "horizontal":
            self.native.setLayout(QHBoxLayout())
        elif layout == "grid":
            self.native.setLayout(QGridLayout())
        else:
            raise ValueError(layout)
        self.native.setContentsMargins(0, 0, 0, 0)
        self._magicclass_parent_ref = None

    def set_widget(self, widget: QWidget, *args):
        """Set the central widget to the widget."""
        self.native.layout().addWidget(widget, *args)
        widget.setParent(self.native)
        self.central_widget = widget

    def remove_widget(self, widget: QWidget):
        """Set the central widget from the widget."""
        self.native.layout().removeWidget(widget)
        widget.setParent(None)
        self.central_widget = None

    def set_contextmenu(self, contextmenugui: ContextMenuGui):
        from .._gui import ContextMenuGui

        if not isinstance(contextmenugui, ContextMenuGui):
            raise TypeError
        from .._gui.utils import set_context_menu

        set_context_menu(contextmenugui, self)

    @property
    def __magicclass_parent__(self) -> BaseGui | None:
        """Return parent magic class if exists."""
        if self._magicclass_parent_ref is None:
            return None
        parent = self._magicclass_parent_ref()
        return parent

    @__magicclass_parent__.setter
    def __magicclass_parent__(self, parent) -> None:
        if parent is None:
            return
        self._magicclass_parent_ref = weakref.ref(parent)


WIDGET_OPTIONS = frozenset(
    {
        "name",
        "annotation",
        "label",
        "tooltip",
        "visible",
        "enabled",
        "gui_only",
    }
)


class _MagicWidgetMeta(type):
    def __new__(
        mcls,
        name: str,
        bases: tuple,
        namespace: dict,
        base: type[QWidget] | None = None,
    ) -> _MagicWidgetMeta:
        cls: _MagicWidgetMeta = type.__new__(mcls, name, bases, namespace)
        if base is None:
            return cls
        if not issubclass(base, QWidget):
            raise TypeError("The base parameter must be a subclass of QWidget.")

        cls.__init__ = cls._define_init(cls, base)
        return cls

    @staticmethod
    def _define_init(base_cls: type, base_qwidget: type[QWidget]):
        cls_init = base_cls.__init__

        def __init__(self, *args, **kwargs):
            widget_options: dict[str, Any] = {}
            qt_options: dict[str, Any] = {}
            for k, v in kwargs.items():
                if k in WIDGET_OPTIONS:
                    widget_options[k] = v
                else:
                    qt_options[k] = v

            Widget.__init__(
                self,
                widget_type=QBaseWidget,
                backend_kwargs={"qwidg": base_qwidget},
                **widget_options,
            )
            cls_init(self, *args, **qt_options)

        return __init__


class MagicWidgetBase(Widget, metaclass=_MagicWidgetMeta):
    """
    An abstract class to convert QWidget into magicgui's Widget class.

    .. code-block:: python

        class MyQWidget(QWidget):
            ...

        class MyWidget(MagicGuiBase, base=MyQWidget):
            ...
    """

    def __init__(self):
        pass


class _ValueWidgetProtocol(QBaseWidget, _protocols.ValueWidgetProtocol):
    def __init__(self, qwidg: QWidget):
        super().__init__(qwidg)

    def _mgui_get_value(self) -> Any:
        return self._qwidget._mgui_get_value()

    def _mgui_set_value(self, val) -> None:
        self._qwidget._mgui_set_value(val)

    def _mgui_bind_change_callback(self, callback):
        self._qwidget._mgui_bind_change_callback(callback)


VALUE_WIDGET_OPTIONS = WIDGET_OPTIONS | frozenset({"value", "nullable", "bind"})


class _MagicValueWidgetMeta(_MagicWidgetMeta):
    @staticmethod
    def _define_init(base_cls, base_qwidget: type[QWidget]):
        cls_init = base_cls.__init__

        def __init__(self, *args, **kwargs):
            widget_options: dict[str, Any] = {}
            qt_options: dict[str, Any] = {}
            for k, v in kwargs.items():
                if k in VALUE_WIDGET_OPTIONS:
                    widget_options[k] = v
                else:
                    qt_options[k] = v

            protocol = type(f"{base_cls.__name__}Protocol", (_ValueWidgetProtocol,), {})

            ValueWidget.__init__(
                self,
                widget_type=protocol,
                backend_kwargs={"qwidg": base_qwidget},
                **widget_options,
            )
            cls_init(self, *args, **qt_options)

        return __init__


class MagicValueWidgetBase(ValueWidget, metaclass=_MagicValueWidgetMeta):
    def __init__(self):
        pass

    def _mgui_get_value(self):
        raise NotImplementedError()

    def _mgui_set_value(self, value):
        raise NotImplementedError()

    def _mgui_bind_change_callback(self, callback):
        raise NotImplementedError()


class _RangedWidgetProtocol(QBaseWidget, _protocols.RangedWidgetProtocol):
    def __init__(self, qwidg: QWidget):
        super().__init__(qwidg)

    def _mgui_get_value(self) -> Any:
        return self._qwidget._mgui_get_value()

    def _mgui_set_value(self, val) -> None:
        self._qwidget._mgui_set_value(val)

    def _mgui_bind_change_callback(self, callback):
        self._qwidget._mgui_bind_change_callback(callback)

    def _mgui_get_min(self) -> Any:
        return self._qwidget._mgui_get_min()

    def _mgui_set_min(self, value: float) -> None:
        self._qwidget._mgui_set_min(value)

    def _mgui_get_max(self) -> float:
        return self._qwidget._mgui_get_max()

    def _mgui_set_max(self, value: float) -> None:
        self._qwidget._mgui_set_max(value)

    def _mgui_get_step(self) -> float:
        return self._qwidget._mgui_get_step()

    def _mgui_set_step(self, value: float) -> None:
        self._qwidget._mgui_set_step(value)

    def _mgui_get_adaptive_step(self) -> float:
        raise self._qwidget._mgui_get_adaptive_step()

    def _mgui_set_adaptive_step(self, value: float) -> None:
        self._qwidget._mgui_set_adaptive_step(value)


RANGED_WIDGET_OPTIONS = VALUE_WIDGET_OPTIONS | frozenset(
    {
        "min",
        "max",
        "step",
    }
)


class _MagicRangedWidgetMeta(_MagicValueWidgetMeta):
    @staticmethod
    def _define_init(base_cls, base_qwidget: type[QWidget]):
        cls_init = base_cls.__init__

        def __init__(self, *args, **kwargs):
            widget_options: dict[str, Any] = {}
            qt_options: dict[str, Any] = {}
            for k, v in kwargs.items():
                if k in VALUE_WIDGET_OPTIONS:
                    widget_options[k] = v
                else:
                    qt_options[k] = v

            protocol = type(
                f"{base_cls.__name__}Protocol", (_RangedWidgetProtocol,), {}
            )

            ValueWidget.__init__(
                self,
                widget_type=protocol,
                backend_kwargs={"qwidg": base_qwidget},
                **widget_options,
            )
            cls_init(self, *args, **qt_options)

        return __init__


class MagicRangedWidgetBase(RangedWidget, metaclass=_MagicRangedWidgetMeta):
    def __init__(self):
        pass

    def _mgui_get_value(self):
        raise NotImplementedError()

    def _mgui_set_value(self, value):
        raise NotImplementedError()

    def _mgui_bind_change_callback(self, callback):
        raise NotImplementedError()

    def _mgui_get_min(self) -> Any:
        raise NotImplementedError()

    def _mgui_set_min(self, value: float) -> None:
        raise NotImplementedError()

    def _mgui_get_max(self) -> float:
        raise NotImplementedError()

    def _mgui_set_max(self, value: float) -> None:
        raise NotImplementedError()

    def _mgui_get_step(self) -> float:
        raise NotImplementedError()

    def _mgui_set_step(self, value: float) -> None:
        raise NotImplementedError()

    def _mgui_get_adaptive_step(self) -> float:
        raise NotImplementedError()

    def _mgui_set_adaptive_step(self, value: float) -> None:
        raise NotImplementedError()


def merge_super_sigs(cls):
    cls = _merge_super_sigs(cls)
    cls.__module__ = "magicclass.widgets"
    return cls
