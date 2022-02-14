from __future__ import annotations
from typing import Callable, TYPE_CHECKING, Any
import warnings
from inspect import signature
from magicgui.widgets import Image, Table, Label, FunctionGui
from magicgui.widgets._bases import ButtonWidget
from magicgui.widgets._bases.widget import Widget
from macrokit import Symbol
from qtpy.QtWidgets import QToolBar, QMenu, QWidgetAction, QTabWidget
from qtpy.QtCore import Qt

from .mgui_ext import AbstractAction, _LabeledWidgetAction, WidgetAction, ToolButtonPlus
from ._base import (
    BaseGui,
    PopUpMode,
    ErrorMode,
    ContainerLikeGui,
    nested_function_gui_callback,
)
from .utils import MagicClassConstructionError, define_context_menu
from .menu_gui import ContextMenuGui, MenuGui, MenuGuiBase, insert_action_like

from ..signature import get_additional_option
from ..fields import MagicField
from ..widgets import FreeWidget, Separator
from ..utils import iter_members

if TYPE_CHECKING:
    from napari.viewer import Viewer


def _check_popupmode(popup_mode: PopUpMode):
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first):
        msg = (
            f"magictoolbar does not support popup mode {popup_mode.value}."
            "PopUpMode.popup is used instead"
        )
        warnings.warn(msg, UserWarning)
    elif popup_mode == PopUpMode.last:
        msg = (
            f"magictoolbat does not support popup mode {popup_mode.value}."
            "PopUpMode.parentlast is used instead"
        )
        warnings.warn(msg, UserWarning)
        popup_mode = PopUpMode.parentlast

    return popup_mode


class QtTabToolBar(QToolBar):
    """ToolBar widget with tabs."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._tab = QTabWidget(self)
        self._tab.setContentsMargins(0, 0, 0, 0)
        self._tab.setTabBarAutoHide(True)
        self._tab.setStyleSheet(
            "QTabWidget {" "    margin: 0px, 0px, 0px, 0px;" "    padding: 0px;}"
        )
        self.addWidget(self._tab)

    def addToolBar(self, toolbar: QToolBar, name: str) -> None:
        """Add a toolbar as a tab."""
        self._tab.addTab(toolbar, name)
        toolbar.setContentsMargins(0, 0, 0, 0)
        return None


class ToolBarGui(ContainerLikeGui):
    """Magic class that will be converted into a toolbar"""

    def __init__(
        self,
        parent=None,
        name: str = None,
        close_on_run: bool = None,
        popup_mode: str | PopUpMode = None,
        error_mode: str | ErrorMode = None,
        labels: bool = True,
    ):
        popup_mode = _check_popupmode(popup_mode)

        super().__init__(
            close_on_run=close_on_run, popup_mode=popup_mode, error_mode=error_mode
        )
        name = name or self.__class__.__name__
        self.native = QToolBar(name, parent)
        self.name = name
        self._list: list[MenuGuiBase | AbstractAction] = []
        self.labels = labels

    def reset_choices(self, *_: Any):
        """Reset child Categorical widgets"""
        for widget in self:
            if hasattr(widget, "reset_choices"):
                widget.reset_choices()
        for widget in self.__magicclass_children__:
            if hasattr(widget, "reset_choices"):
                widget.reset_choices()

        # If parent magic-class is added to napari viewer, the style sheet need update because
        # QToolButton has inappropriate style.
        # Detecting this event using "reset_choices" is not a elegant way, but works for now.
        viewer = self.parent_viewer
        style = _create_stylesheet(viewer)
        self.native.setStyleSheet(style)

    def _convert_attributes_into_widgets(self):
        cls = self.__class__

        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)

        # Bind all the methods and annotations
        base_members = {x[0] for x in iter_members(ToolBarGui)}

        _hist: list[tuple[str, str, str]] = []  # for traceback

        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if isinstance(attr, property):
                continue

            try:
                if isinstance(attr, type):
                    if not issubclass(attr, BaseGui):
                        continue
                    # Nested magic-menu
                    widget = attr()
                    object.__setattr__(self, name, widget)

                elif isinstance(attr, MagicField):
                    widget = self._create_widget_from_field(name, attr)

                else:
                    # convert class method into instance method
                    widget = getattr(self, name, None)

                if name.startswith("_"):
                    continue

                if isinstance(widget, FunctionGui):
                    p0 = list(signature(attr).parameters)[0]
                    getattr(widget, p0).bind(self)  # set self to the first argument

                elif isinstance(widget, BaseGui):
                    widget.__magicclass_parent__ = self
                    self.__magicclass_children__.append(widget)
                    widget._my_symbol = Symbol(name)

                    if isinstance(widget, MenuGui):
                        tb = ToolButtonPlus(widget.name)
                        tb.set_menu(widget.native)
                        tb.tooltip = widget.__doc__
                        widget = WidgetAction(tb)

                    elif isinstance(widget, ContextMenuGui):
                        # Add context menu to toolbar
                        self.native.setContextMenuPolicy(Qt.CustomContextMenu)
                        self.native.customContextMenuRequested.connect(
                            define_context_menu(widget, self.native)
                        )
                        _hist.append((name, type(attr), "ContextMenuGui"))

                    elif isinstance(widget, ToolBarGui):
                        tb = ToolButtonPlus(widget.name)
                        tb.tooltip = widget.__doc__
                        qmenu = QMenu(self.native)
                        waction = QWidgetAction(qmenu)
                        waction.setDefaultWidget(widget.native)
                        qmenu.addAction(waction)
                        tb.set_menu(qmenu)
                        widget = WidgetAction(tb)

                    else:
                        widget = WidgetAction(widget)

                elif isinstance(widget, Widget):
                    widget = WidgetAction(widget)

                if isinstance(widget, (AbstractAction, Callable, Widget)):
                    if (not isinstance(widget, Widget)) and callable(widget):
                        widget = self._create_widget_from_method(widget)

                    elif hasattr(widget, "__magicclass_parent__") or hasattr(
                        widget.__class__, "__magicclass_parent__"
                    ):
                        if isinstance(widget, BaseGui):
                            widget._my_symbol = Symbol(name)
                        # magic-class has to know its parent.
                        # if __magicclass_parent__ is defined as a property, hasattr must be called
                        # with a type object (not instance).
                        widget.__magicclass_parent__ = self

                    moveto = get_additional_option(attr, "into")
                    copyto = get_additional_option(attr, "copyto", [])
                    if moveto is not None or copyto:
                        self._unwrap_method(name, widget, moveto, copyto)
                    else:
                        self.insert(len(self), widget)

                    _hist.append((name, str(type(attr)), type(widget).__name__))

            except Exception as e:
                hist_str = (
                    "\n\t".join(map(lambda x: f"{x[0]} {x[1]} -> {x[2]}", _hist))
                    + f"\n\t\t{name} ({type(attr)}) <--- Error"
                )
                if not hist_str.startswith("\n\t"):
                    hist_str = "\n\t" + hist_str
                if isinstance(e, MagicClassConstructionError):
                    e.args = (f"\n{hist_str}\n{e}",)
                    raise e
                else:
                    raise MagicClassConstructionError(
                        f"{hist_str}\n\n{type(e).__name__}: {e}"
                    ) from e

        self._unify_label_widths()
        return None

    def _fast_insert(self, key: int, obj: AbstractAction | Callable) -> None:
        """
        Insert object into the toolbar. Could be widget or callable.

        Parameters
        ----------
        key : int
            Position to insert.
        obj : Callable or AbstractAction
            Object to insert.
        """
        if isinstance(obj, Callable):
            # Sometimes uses want to dynamically add new functions to GUI.
            method_name = getattr(obj, "__name__", None)
            if method_name and not hasattr(self, method_name):
                object.__setattr__(self, method_name, obj)

            if isinstance(obj, FunctionGui):
                if obj.parent is None:
                    f = nested_function_gui_callback(self, obj)
                    obj.called.connect(f)
            else:
                obj = self._create_widget_from_method(obj)

        # _hide_labels should not contain Container because some ValueWidget like widgets
        # are Containers.
        if isinstance(obj, self._component_class):
            insert_action_like(self.native, key, obj.native)
            self._list.insert(key, obj)

        elif isinstance(obj, WidgetAction):
            if isinstance(obj.widget, Separator):
                insert_action_like(self.native, key, "sep")

            else:
                _hide_labels = (
                    _LabeledWidgetAction,
                    ButtonWidget,
                    FreeWidget,
                    Label,
                    FunctionGui,
                    Image,
                    Table,
                )
                _obj = obj
                if (not isinstance(obj.widget, _hide_labels)) and self.labels:
                    _obj = _LabeledWidgetAction.from_action(obj)
                _obj.parent = self
                insert_action_like(self.native, key, _obj.native)
            self._list.insert(key, obj)
        else:
            raise TypeError(f"{type(obj)} is not supported.")

    def insert(self, key: int, obj: AbstractAction) -> None:
        self._fast_insert(key, obj)
        self._unify_label_widths()


def _create_stylesheet(viewer: Viewer):
    if viewer is None:
        return ""
    w = viewer.window._qt_window
    styles = []
    for s in w.styleSheet().split("\n\n"):
        if s.startswith("QPushButton ") or s.startswith("QPushButton:"):
            styles.append("QToolButton" + s[11:])
    return "\n".join(styles)
