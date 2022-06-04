from __future__ import annotations
from typing import Callable
import warnings
from magicgui.widgets import Image, Table, Label, FunctionGui
from magicgui.widgets._bases import ButtonWidget
from magicgui.widgets._bases.widget import Widget
from macrokit import Symbol
from qtpy.QtWidgets import QMenu

from .mgui_ext import AbstractAction, WidgetAction, _LabeledWidgetAction
from .keybinding import register_shortcut
from ._base import (
    BaseGui,
    PopUpMode,
    ErrorMode,
    ContainerLikeGui,
    nested_function_gui_callback,
    _inject_recorder,
)
from .utils import copy_class, format_error

from ..signature import get_additional_option
from ..fields import MagicField
from ..widgets import Separator, FreeWidget
from ..utils import iter_members


def _check_popupmode(popup_mode: PopUpMode):
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first):
        msg = (
            f"magicmenu does not support popup mode {popup_mode.value}."
            "PopUpMode.popup is used instead"
        )
        warnings.warn(msg, UserWarning)
    elif popup_mode == PopUpMode.last:
        msg = (
            f"magicmenu does not support popup mode {popup_mode.value}."
            "PopUpMode.parentlast is used instead"
        )
        warnings.warn(msg, UserWarning)
        popup_mode = PopUpMode.parentlast

    return popup_mode


class MenuGuiBase(ContainerLikeGui):
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
        self.native = QMenu(name, parent)
        self.native.setToolTipsVisible(True)
        self.name = name
        self._list: list[MenuGuiBase | AbstractAction] = []
        self.labels = labels

    def _convert_attributes_into_widgets(self):
        cls = self.__class__

        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)

        # Bind all the methods and annotations
        base_members = {x[0] for x in iter_members(MenuGuiBase)}

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

                    if isinstance(widget, MenuGuiBase):
                        widget.native.setParent(
                            self.native, widget.native.windowFlags()
                        )

                    else:
                        widget = WidgetAction(widget)

                elif isinstance(widget, Widget):
                    if not widget.name:
                        widget.name = name
                    if hasattr(widget, "text") and not widget.text:
                        widget.text = widget.name.replace("_", " ")
                    widget = WidgetAction(widget)

                if isinstance(widget, (MenuGuiBase, AbstractAction, Callable, Widget)):
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
                        self._fast_insert(len(self), widget)

                    _hist.append((name, str(type(attr)), type(widget).__name__))

            except Exception as e:
                format_error(e, _hist, name, attr)

        self._unify_label_widths()
        return None

    def _fast_insert(
        self, key: int, obj: Callable | MenuGuiBase | AbstractAction
    ) -> None:
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

        if isinstance(_obj, (self._component_class, MenuGuiBase)):
            insert_action_like(self.native, key, _obj.native)
            self._list.insert(key, _obj)

        elif isinstance(_obj, WidgetAction):
            from .toolbar import ToolBarGui

            if isinstance(_obj.widget, Separator):
                insert_action_like(self.native, key, _obj.widget.title)

            elif isinstance(_obj.widget, ToolBarGui):
                qmenu = QMenu(_obj.widget.name, self.native)
                qmenu.addAction(_obj.native)
                if _obj.widget._icon_path is not None:
                    qmenu.setIcon(_obj.widget.native.windowIcon())
                insert_action_like(self.native, key, qmenu)

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

    def insert(self, key: int, obj: Callable | MenuGuiBase | AbstractAction) -> None:
        """
        Insert object into the menu. Could be widget or callable.

        Parameters
        ----------
        key : int
            Position to insert.
        obj : Callable | MenuGuiBase | AbstractAction | Widget
            Object to insert.
        """
        self._fast_insert(key, obj)
        self._unify_label_widths()


def insert_action_like(qmenu: QMenu, key: int, obj):
    """
    Insert a QObject into a QMenu in a Pythonic way, like qmenu.insert(key, obj).

    Parameters
    ----------
    qmenu : QMenu
        QMenu object to which object will be inserted.
    key : int
        Position to insert.
    obj : QMenu or QAction or str
        Object to be inserted.
    """
    actions = qmenu.actions()
    l = len(actions)
    if key < 0:
        key = key + l
    if key == l:
        if isinstance(obj, QMenu):
            qmenu.addMenu(obj).setText(obj.objectName().replace("_", " "))
        elif isinstance(obj, str):
            if obj:
                qmenu.addSection(obj)
            else:
                qmenu.addSeparator()
        else:
            qmenu.addAction(obj)
    else:
        new_action = actions[key]
        before = new_action
        if isinstance(obj, QMenu):
            qmenu.insertMenu(before, obj).setText(obj.objectName().replace("_", " "))
        elif isinstance(obj, str):
            if obj:
                qmenu.insertSection(before, obj)
            else:
                qmenu.insertSeparator(before)
        else:
            qmenu.insertAction(before, obj)


class MenuGui(MenuGuiBase):
    """Magic class that will be converted into a menu bar."""


class ContextMenuGui(MenuGuiBase):
    """Magic class that will be converted into a context menu."""

    # TODO: Prevent more than one context menu
