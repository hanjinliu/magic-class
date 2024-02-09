from __future__ import annotations
from typing import Callable, TYPE_CHECKING
import warnings
from magicgui.widgets import Image, Table, Label, FunctionGui, Widget
from magicgui.widgets.bases import ButtonWidget
from macrokit import Symbol
from psygnal import Signal
from qtpy.QtWidgets import QToolBar, QMenu, QWidgetAction, QTabWidget

from .mgui_ext import (
    AbstractAction,
    _LabeledWidgetAction,
    WidgetAction,
    ToolButtonPlus,
    PaletteEvents,
)
from .keybinding import register_shortcut
from ._base import (
    BaseGui,
    PopUpMode,
    ErrorMode,
    ContainerLikeGui,
    normalize_insertion,
)
from .utils import format_error, connect_magicclasses
from .menu_gui import ContextMenuGui, MenuGui, MenuGuiBase, insert_action_like

from magicclass.signature import get_additional_option
from magicclass.widgets import FreeWidget, Separator
from magicclass.utils import iter_members, Tooltips

if TYPE_CHECKING:
    import napari


def _check_popupmode(popup_mode: PopUpMode):
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first):
        msg = (
            f"magictoolbar does not support popup mode {popup_mode.value}."
            "PopUpMode.popup is used instead"
        )
        warnings.warn(msg, UserWarning)
    elif popup_mode == PopUpMode.last:
        msg = (
            f"magictoolbar does not support popup mode {popup_mode.value}."
            "PopUpMode.parentlast is used instead"
        )
        warnings.warn(msg, UserWarning)
        popup_mode = PopUpMode.parentlast

    return popup_mode


class QtTabToolBar(QToolBar):
    """ToolBar widget with tabs."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._palette_event_filter = PaletteEvents(self)
        self._tab = QTabWidget(self)
        self._tab.setContentsMargins(0, 0, 0, 0)
        self._tab.setTabBarAutoHide(True)
        self._tab.setStyleSheet(
            "QTabWidget {" "    margin: 0px, 0px, 0px, 0px;" "    padding: 0px;}"
        )
        self.addWidget(self._tab)
        self.installEventFilter(self._palette_event_filter)

    def addToolBar(self, toolbar: QToolBar, name: str) -> None:
        """Add a toolbar as a tab."""
        self._tab.addTab(toolbar, name)
        toolbar.setContentsMargins(0, 0, 0, 0)
        return None


class _QToolBar(QToolBar):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._palette_event_filter = PaletteEvents(self)
        self.installEventFilter(self._palette_event_filter)


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
        self._native = _QToolBar(name, parent)
        self.name = name
        self._list: list[MenuGuiBase | AbstractAction] = []
        self.labels = labels
        self._native._palette_event_filter.paletteChanged.connect(self._update_icon)

    @property
    def native(self):
        """The native Qt widget."""
        return self._native

    def _update_icon(self):
        viewer = self.parent_viewer
        if viewer is not None:
            self._native._palette_event_filter.blockSignals(True)
            try:
                style = _create_stylesheet(viewer)
                self.native.setStyleSheet(style)
            finally:
                self._native._palette_event_filter.blockSignals(False)

        return super()._update_icon()

    def _convert_attributes_into_widgets(self):
        cls = self.__class__

        # Add class docstring as tooltip.
        _tooltips = Tooltips(cls)
        self.native.setToolTip(_tooltips.desc)

        # Bind all the methods and annotations
        base_members = {x[0] for x in iter_members(ToolBarGui)}

        _hist: list[tuple[str, str, str]] = []  # for traceback
        _ignore_types = (property, classmethod, staticmethod)

        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if isinstance(attr, _ignore_types):
                continue

            try:
                widget = self._convert_an_attribute_into_widget(name, attr, _tooltips)

                if isinstance(widget, BaseGui):
                    if isinstance(widget, MenuGui):
                        tb = ToolButtonPlus(widget.name, parent=self.native)
                        tb.set_menu(widget.native, widget.icon)
                        widget.native.setParent(tb.native, widget.native.windowFlags())
                        tb.tooltip = Tooltips(widget).desc
                        widget = WidgetAction(tb)

                    elif isinstance(widget, ContextMenuGui):
                        # Add context menu to toolbar
                        widget._set_magic_context_menu(self)
                        _hist.append((name, type(attr), "ContextMenuGui"))

                    elif isinstance(widget, ToolBarGui):
                        tb = ToolButtonPlus(widget.name, parent=self.native)
                        tb.tooltip = Tooltips(widget).desc
                        qmenu = QMenu(self.native)
                        waction = QWidgetAction(qmenu)
                        waction.setDefaultWidget(widget.native)
                        qmenu.addAction(waction)
                        tb.set_menu(qmenu, widget.icon)
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
                        if isinstance(widget, Signal):
                            continue
                        widget = self._create_widget_from_method(widget)

                        # contextmenu
                        contextmenu = get_additional_option(attr, "context_menu", None)
                        if contextmenu is not None:
                            contextmenu: ContextMenuGui
                            contextmenu._set_magic_context_menu(widget)
                            connect_magicclasses(self, contextmenu, contextmenu.name)

                    elif hasattr(widget, "__magicclass_parent__") or hasattr(
                        widget.__class__, "__magicclass_parent__"
                    ):
                        if isinstance(widget, BaseGui):
                            widget._my_symbol = Symbol(name)
                        # magic-class has to know its parent.
                        # if __magicclass_parent__ is defined as a property, hasattr
                        # must be called with a type object (not instance).
                        widget.__magicclass_parent__ = self

                    if widget.name.startswith("_"):
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

    def _fast_insert(
        self, key: int, obj: AbstractAction | Callable, remove_label: bool = False
    ) -> None:
        """
        Insert object into the toolbar. Could be widget or callable.

        Parameters
        ----------
        key : int
            Position to insert.
        obj : Callable or AbstractAction
            Object to insert.
        """
        _obj = normalize_insertion(self, obj)

        # _hide_labels should not contain Container because some ValueWidget like
        # widgets are Containers.
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
                _obj_labeled = _obj
                if self.labels:
                    if not isinstance(_obj.widget, _hide_labels) and not remove_label:
                        _obj_labeled = _LabeledWidgetAction.from_action(_obj)
                _obj_labeled.parent = self
                insert_action_like(self.native, key, _obj_labeled.native)
            self._list.insert(key, _obj)
        else:
            raise TypeError(f"{type(_obj)} is not supported.")

    def insert(self, key: int, obj: AbstractAction) -> None:
        self._fast_insert(key, obj)
        self._unify_label_widths()


def _create_stylesheet(viewer: napari.Viewer):
    if viewer is None:
        return ""
    w = viewer.window._qt_window
    styles = []
    for s in w.styleSheet().split("\n\n"):
        if s.startswith("QPushButton ") or s.startswith("QPushButton:"):
            styles.append("QToolButton" + s[11:])
    return "\n".join(styles)
