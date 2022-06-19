from __future__ import annotations
from typing import Callable, TYPE_CHECKING, Any
import warnings
from magicgui.widgets import Image, Table, Label, FunctionGui
from magicgui.widgets._bases import ButtonWidget
from magicgui.widgets._bases.widget import Widget
from macrokit import Symbol
from qtpy.QtWidgets import QToolBar, QMenu, QWidgetAction, QTabWidget


from .mgui_ext import AbstractAction, _LabeledWidgetAction, WidgetAction, ToolButtonPlus
from .keybinding import register_shortcut
from ._base import (
    BaseGui,
    PopUpMode,
    ErrorMode,
    ContainerLikeGui,
    nested_function_gui_callback,
    _inject_recorder,
)
from .utils import copy_class, format_error, set_context_menu
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
        super().reset_choices()

        # If parent magic-class is added to napari viewer, the style sheet need update because
        # QToolButton has inappropriate style.
        # Detecting this event using "reset_choices" is not a elegant way, but works for now.
        viewer = self.parent_viewer
        if viewer is not None:
            style = _create_stylesheet(viewer)
            self.native.setStyleSheet(style)
        return None

    def _convert_attributes_into_widgets(self):
        cls = self.__class__

        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)

        # Bind all the methods and annotations
        base_members = {x[0] for x in iter_members(ToolBarGui)}

        _hist: list[tuple[str, str, str]] = []  # for traceback
        _ignore_types = (property, classmethod, staticmethod)

        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if isinstance(attr, _ignore_types):
                continue

            try:
                if isinstance(attr, type):
                    # Nested magic-menu
                    if cls.__name__ not in attr.__qualname__.split("."):
                        attr = copy_class(attr, ns=cls)
                    widget = attr()
                    object.__setattr__(self, name, widget)

                elif isinstance(attr, MagicField):
                    widget = self._create_widget_from_field(name, attr)

                else:
                    # convert class method into instance method
                    widget = getattr(self, name, None)

                if isinstance(widget, FunctionGui):
                    widget[0].bind(self)  # set self to the first argument

                elif isinstance(widget, BaseGui):
                    widget.__magicclass_parent__ = self
                    self.__magicclass_children__.append(widget)
                    widget._my_symbol = Symbol(name)

                    if isinstance(widget, MenuGui):
                        tb = ToolButtonPlus(widget.name)
                        tb.set_menu(widget.native)
                        widget.native.setParent(tb.native, widget.native.windowFlags())
                        tb.tooltip = widget.__doc__
                        widget = WidgetAction(tb)

                    elif isinstance(widget, ContextMenuGui):
                        # Add context menu to toolbar
                        set_context_menu(widget, self)
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
                        if name.startswith("_") or not get_additional_option(
                            attr, "gui", True
                        ):
                            keybinding = get_additional_option(attr, "keybinding", None)
                            if keybinding:
                                register_shortcut(
                                    keys=keybinding, parent=self.native, target=widget
                                )
                            continue
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

                    if name.startswith("_"):
                        continue

                    moveto = get_additional_option(attr, "into")
                    copyto = get_additional_option(attr, "copyto", [])
                    if moveto is not None or copyto:
                        self._unwrap_method(name, widget, moveto, copyto)
                    else:
                        self.insert(len(self), widget)

                    _hist.append((name, str(type(attr)), type(widget).__name__))

            except Exception as e:
                format_error(e, _hist, name, attr)

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
            # Sometimes users want to dynamically add new functions to GUI.
            if isinstance(obj, FunctionGui):
                if obj.parent is None:
                    f = nested_function_gui_callback(self, obj)
                    obj.called.connect(f)
                _obj = obj
            else:
                obj = _inject_recorder(obj, is_method=False).__get__(self)
                _obj = self._create_widget_from_method(obj)

            method_name = getattr(obj, "__name__", None)
            if method_name and not hasattr(self, method_name):
                object.__setattr__(self, method_name, obj)
        else:
            _obj = obj

        # _hide_labels should not contain Container because some ValueWidget like widgets
        # are Containers.
        if isinstance(_obj, self._component_class):
            insert_action_like(self.native, key, _obj.native)
            self._list.insert(key, _obj)

        elif isinstance(_obj, WidgetAction):
            if isinstance(_obj.widget, Separator):
                insert_action_like(self.native, key, "")

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
                _obj = _obj
                if (not isinstance(_obj.widget, _hide_labels)) and self.labels:
                    _obj = _LabeledWidgetAction.from_action(_obj)
                _obj.parent = self
                insert_action_like(self.native, key, _obj.native)
            self._list.insert(key, _obj)
        else:
            raise TypeError(f"{type(_obj)} is not supported.")

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
