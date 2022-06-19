from __future__ import annotations
from typing import Any, Callable, Sequence, TypeVar
import warnings
from qtpy.QtWidgets import QMenuBar, QWidget, QMainWindow, QBoxLayout, QDockWidget
from qtpy.QtCore import Qt
from magicgui.widgets import Container, MainWindow, Label, FunctionGui, Image, Table
from magicgui.widgets._bases import Widget, ButtonWidget, ValueWidget, ContainerWidget
from magicgui.widgets._concrete import _LabeledWidget, ContainerWidget
from macrokit import Symbol


from .keybinding import register_shortcut
from .mgui_ext import PushButtonPlus
from .toolbar import ToolBarGui, QtTabToolBar
from .menu_gui import MenuGui, ContextMenuGui
from ._base import (
    BaseGui,
    PopUpMode,
    ErrorMode,
    value_widget_callback,
    nested_function_gui_callback,
)
from .utils import (
    copy_class,
    format_error,
    set_context_menu,
)
from ..widgets import (
    ButtonContainer,
    GroupBoxContainer,
    FrameContainer,
    ListContainer,
    SubWindowsContainer,
    ScrollableContainer,
    DraggableContainer,
    CollapsibleContainer,
    HCollapsibleContainer,
    SplitterContainer,
    StackedContainer,
    TabbedContainer,
    ToolBoxContainer,
    FreeWidget,
)

from ..utils import iter_members, Tooltips
from ..fields import MagicField
from ..signature import get_additional_option
from .._app import run_app

# For Containers that belong to these classes, menubar must be set to _qwidget.layout().
_USE_OUTER_LAYOUT = (
    ScrollableContainer,
    DraggableContainer,
    SplitterContainer,
    TabbedContainer,
)

_MCLS_PAREMT = "__magicclass_parent__"


class ClassGuiBase(BaseGui):
    # This class is always inherited by @magicclass decorator.
    _component_class = PushButtonPlus
    _container_widget: type
    _remove_child_margins: bool
    native: QWidget

    def _create_widget_from_field(self, name: str, fld: MagicField):
        if fld.not_ready():
            raise TypeError(
                f"MagicField {name} does not contain enough information for widget creation"
            )

        fld.name = fld.name or name
        widget = fld.get_widget(self)

        if isinstance(widget, BaseGui):
            widget.__magicclass_parent__ = self
            self.__magicclass_children__.append(widget)
            widget._my_symbol = Symbol(name)

        if isinstance(widget, (ValueWidget, ContainerWidget)):
            # If the field has callbacks, connect it to the newly generated widget.
            if (
                isinstance(widget, ValueWidget) or hasattr(widget, "value")
            ) and fld.record:
                # By default, set value function will be connected to the widget.
                getvalue = type(fld) is MagicField
                f = value_widget_callback(self, widget, name, getvalue=getvalue)
                widget.changed.connect(f)

        elif fld.callbacks:
            warnings.warn(
                f"{type(widget).__name__} does not have value-change callback. "
                "Connecting callback functions does no effect.",
                UserWarning,
            )

        return widget

    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and nested
        classes are converted to magicgui widgets.
        """
        cls = self.__class__

        # Add class docstring as tooltip.
        _tooltips = Tooltips(cls)
        self.tooltip = _tooltips.desc

        # Bind all the methods and annotations
        n_insert = 0
        base_members = {x[0] for x in iter_members(self._container_widget)}
        base_members |= {x[0] for x in iter_members(ClassGuiBase)}

        _hist: list[tuple[str, str, str]] = []  # for traceback
        _annot = ClassGuiBase.__annotations__.keys()
        _ignore_types = (property, classmethod, staticmethod)
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if name in _annot or isinstance(attr, _ignore_types):
                continue

            try:
                if isinstance(attr, type):
                    # Nested magic-class
                    if cls.__name__ not in attr.__qualname__.split("."):
                        attr = copy_class(attr, ns=cls)
                    widget = attr()
                    object.__setattr__(self, name, widget)

                elif isinstance(attr, MagicField):
                    # If MagicField is given by field() function.
                    widget = self._create_widget_from_field(name, attr)
                    if not widget.tooltip:
                        widget.tooltip = _tooltips.attributes.get(name, "")

                elif isinstance(attr, FunctionGui):
                    widget = attr.copy()
                    widget[0].bind(self)  # bind self to the first argument

                else:
                    # convert class method into instance method
                    widget = getattr(self, name, None)

                if isinstance(widget, BaseGui):
                    widget.__magicclass_parent__ = self
                    self.__magicclass_children__.append(widget)
                    widget._my_symbol = Symbol(name)

                if isinstance(widget, MenuGui):
                    # Add menubar to container
                    if self._menubar is None:
                        # if widget has no menubar, a new one should be created.
                        self._menubar = QMenuBar(parent=self.native)
                        if issubclass(self.__class__, MainWindow):
                            self.native: QMainWindow
                            self.native.setMenuBar(self._menubar)
                        else:
                            if hasattr(self._widget, "_scroll_area"):
                                _layout: QBoxLayout = self._widget._qwidget.layout()
                            else:
                                _layout = self._widget._layout
                            if _layout.menuBar() is None:
                                _layout.setMenuBar(self._menubar)
                            else:
                                raise RuntimeError(
                                    "Cannot add menubar after adding a toolbar in a non-main window. "
                                    "Use maigcclass(widget_type='mainwindow') instead, or define the "
                                    "menu class before toolbar class."
                                )

                    widget.native.setParent(self._menubar, widget.native.windowFlags())
                    self._menubar.addMenu(widget.native).setText(
                        widget.name.replace("_", " ")
                    )
                    _hist.append((name, type(attr), "MenuGui"))

                elif isinstance(widget, ContextMenuGui):
                    # Add context menu to container
                    set_context_menu(widget, self)
                    _hist.append((name, type(attr), "ContextMenuGui"))

                elif isinstance(widget, ToolBarGui):
                    if self._toolbar is None:
                        self._toolbar = QtTabToolBar(widget.name, self.native)
                        if issubclass(self.__class__, MainWindow):
                            self.native: QMainWindow
                            self.native.addToolBar(self._toolbar)
                        else:
                            # self is not a main window object
                            # TODO: these codes are too dirty...
                            if isinstance(self, _USE_OUTER_LAYOUT):
                                _layout: QBoxLayout = self._widget._qwidget.layout()
                            else:
                                _layout = self._widget._layout
                            if _layout.menuBar() is None:
                                _layout.setMenuBar(self._toolbar)
                            else:
                                _layout.insertWidget(
                                    0, self._toolbar, alignment=Qt.AlignTop
                                )
                                self._toolbar.setContentsMargins(0, 0, 0, 0)
                                n_insert += 1

                    widget.native.setParent(self._toolbar, widget.native.windowFlags())
                    self._toolbar.addToolBar(
                        widget.native, widget.name.replace("_", " ")
                    )
                    _hist.append((name, type(attr), "ToolBarGui"))

                elif isinstance(widget, (Widget, Callable)):
                    if (not isinstance(widget, Widget)) and callable(widget):
                        # Methods or any callable objects, but FunctionGui is not included.
                        # NOTE: Here any custom callable objects could be given. Some callable
                        # objects can be incompatible (like "Signal" object in magicgui) but
                        # useful. Those callable objects should be passed from widget construction.
                        if name.startswith("_") or not get_additional_option(
                            attr, "gui", True
                        ):
                            keybinding = get_additional_option(attr, "keybinding", None)
                            if keybinding:
                                register_shortcut(
                                    keys=keybinding, parent=self.native, target=widget
                                )
                            continue
                        try:
                            widget = self._create_widget_from_method(widget)
                        except AttributeError as e:
                            warnings.warn(
                                f"Could not convert {widget!r} into a widget "
                                f"due to AttributeError: {e}",
                                UserWarning,
                            )
                            continue

                    elif hasattr(widget, _MCLS_PAREMT) or hasattr(
                        widget.__class__, _MCLS_PAREMT
                    ):
                        # magic-class has to know its parent.
                        # if __magicclass_parent__ is defined as a property, hasattr must be called
                        # with a type object (not instance).
                        widget.__magicclass_parent__ = self

                    else:
                        if not widget.name:
                            widget.name = name
                        if hasattr(widget, "text") and not widget.text:
                            widget.text = widget.name.replace("_", " ")

                    # Now, "widget" is a Widget object. Add widget in a way similar to "insert" method
                    # of Container.
                    if name.startswith("_"):
                        continue

                    moveto = get_additional_option(attr, "into")
                    copyto = get_additional_option(attr, "copyto", [])
                    if moveto is not None or copyto:
                        self._unwrap_method(name, widget, moveto, copyto)
                    else:
                        self._fast_insert(n_insert, widget)
                        n_insert += 1

                    _hist.append((name, str(type(attr)), type(widget).__name__))

            except Exception as e:
                format_error(e, _hist, name, attr)

        self._unify_label_widths()
        return None

    def _fast_insert(self, key: int, obj: Widget | Callable) -> None:
        if isinstance(obj, Callable):
            # Sometimes uses want to dynamically add new functions to GUI.
            if isinstance(obj, FunctionGui):
                if obj.parent is None:
                    f = nested_function_gui_callback(self, obj)
                    obj.called.connect(f)
                widget = obj
            else:
                from ._base import _inject_recorder

                obj = _inject_recorder(obj, is_method=False).__get__(self)
                widget = self._create_widget_from_method(obj)

            method_name = getattr(obj, "__name__", None)
            if method_name and not hasattr(self, method_name):
                object.__setattr__(self, method_name, obj)
        else:
            widget = obj

        # _hide_labels should not contain Container because some ValueWidget like widgets
        # are Containers.
        _hide_labels = (
            _LabeledWidget,
            ButtonWidget,
            ClassGuiBase,
            FreeWidget,
            Label,
            Image,
            Table,
            FunctionGui,
        )

        if isinstance(widget, (ValueWidget, ContainerWidget)):
            widget.changed.connect(lambda: self.changed.emit(self))

        if hasattr(widget, _MCLS_PAREMT) or hasattr(widget.__class__, _MCLS_PAREMT):
            widget.__magicclass_parent__ = self
            if isinstance(widget, ClassGuiBase):
                if self._remove_child_margins:
                    widget.margins = (0, 0, 0, 0)
                if (
                    len(self.__magicclass_children__) > 0
                    and widget is not self.__magicclass_children__[-1]
                ):
                    # nested magic classes are already in the list
                    self.__magicclass_children__.append(widget)
                    widget._my_symbol = Symbol(widget.name)

                # NOTE: This is not safe. Attributes could collision and macro recording
                # may break if not correctly named.

        _widget = widget

        if self.labels:
            # no labels for button widgets (push buttons, checkboxes, have their own)
            if not isinstance(widget, _hide_labels):
                _widget = _LabeledWidget(widget)
                widget.label_changed.connect(self._unify_label_widths)

        if key < 0:
            key += len(self)
        self._list.insert(key, widget)
        self._widget._mgui_insert_widget(key, _widget)
        return None


_C = TypeVar("_C", bound=ContainerWidget)


def make_gui(container: type[_C], no_margin: bool = True) -> type[_C | ClassGuiBase]:
    """
    Make a ClassGui class from a Container widget.
    Because GUI class inherits Container here, functions that need overriden must be defined
    here, not in ClassGuiBase.
    """

    def wrapper(cls_: type[ClassGuiBase]):
        cls: type[_C | ClassGuiBase] = type(
            cls_.__name__, (container, ClassGuiBase), {}
        )

        def __init__(
            self: cls,
            layout: str = "vertical",
            close_on_run: bool = None,
            popup_mode: str | PopUpMode = None,
            error_mode: str | ErrorMode = None,
            labels: bool = True,
            name: str = None,
            visible: bool = None,
        ):

            container.__init__(
                self, layout=layout, labels=labels, name=name, visible=visible
            )
            BaseGui.__init__(
                self,
                close_on_run=close_on_run,
                popup_mode=popup_mode,
                error_mode=error_mode,
            )

            self._menubar = None
            self._toolbar = None

            self.native.setObjectName(self.name)
            self.native.setWindowTitle(self.name)

        # ui["x"] will not return widget if x is a MagicValueField.
        # To ensure __getitem__ returns a Widget, this method should be overriden.
        def __getitem__(self: cls, key):
            """Get item by integer, str, or slice."""
            if isinstance(key, str):
                for widget in self._list:
                    if key == widget.name:
                        return widget
            return container.__getattr__(self, key)

        def __setattr__(self: cls, name: str, value: Any) -> None:
            if not isinstance(getattr(self.__class__, name, None), MagicField):
                container.__setattr__(self, name, value)
            else:
                object.__setattr__(self, name, value)

        def insert(self: cls, key: int, widget: Widget) -> None:
            self._fast_insert(key, widget)
            self._unify_label_widths()
            return None

        def reset_choices(self: cls, *_: Any):
            """Reset child Categorical widgets"""
            all_widgets: set[Widget] = set()

            for item in self._list:
                widget = getattr(item, "_inner_widget", item)
                all_widgets.add(widget)
            for widget in self.__magicclass_children__:
                all_widgets.add(widget)

            for w in all_widgets:
                if hasattr(w, "reset_choices"):
                    w.reset_choices()
            return None

        def show(self: cls, run: bool = True) -> None:
            """
            Show GUI. If any of the parent GUI is a dock widget in napari, then this
            will also show up as a dock widget (floating if in popup mode).

            Parameters
            ----------
            run : bool, default is True
                *Unlike magicgui, this parameter should always be True* unless you want
                to close the window immediately. If true, application gets executed if
                needed.
            """
            if self.__magicclass_parent__ is not None and self.parent is None:
                # If child magic class is closed before, we have to set parent again.
                self.native.setParent(
                    self.__magicclass_parent__.native, self.native.windowFlags()
                )

            viewer = self.parent_viewer
            if viewer is not None and self.parent is not None:
                name = self.parent.objectName()
                if name in viewer.window._dock_widgets and isinstance(
                    self.parent, QDockWidget
                ):
                    viewer.window._dock_widgets[name].show()
                else:
                    _floating = self._popup_mode == PopUpMode.popup
                    _area = "left" if _floating else "right"
                    dock = viewer.window.add_dock_widget(
                        self,
                        name=self.name.replace("_", " ").strip(),
                        area=_area,
                        allowed_areas=["left", "right"],
                    )
                    dock.setFloating(_floating)
            else:
                container.show(self, run=False)
                self.native.activateWindow()
                if run:
                    run_app()
            return None

        def close(self: cls):
            """Close GUI. if this widget is a dock widget, then also close it."""

            current_self = self._search_parent_magicclass()

            viewer = current_self.parent_viewer
            if viewer is not None:
                try:
                    viewer.window.remove_dock_widget(self.parent)
                except Exception:
                    pass

            container.close(self)

            return None

        if issubclass(container, MainWindow):
            # Similar to napari's viewer.window.add_dock_widget.
            # See napari/_qt/widgets/qt_viewer_dock_widget.py
            from ..wrappers import nogui

            # This function will be detected as non-reserved method so that magicclass will
            # try to convert it into widget. Should decorate with @nogui.
            @nogui
            def add_dock_widget(
                self: cls,
                widget: Widget,
                *,
                name: str = "",
                area: str = "right",
                allowed_areas: Sequence[str] | None = None,
            ):
                """
                Add a widget as a dock widget of the main window.
                This method follows napari's "add_dock_widget" method.

                Parameters
                ----------
                widget : Widget
                    Widget that will be converted into a dock widget and added to the main
                    window.
                name : str, optional
                    Name of the dock widget.
                area : str, default is "right"
                    Initial dock widget area.
                allowed_areas : sequence of str, optional
                    Allowed dock widget area. Allow all areas by default.
                """
                from ._dock_widget import QtDockWidget

                name = name or widget.name
                dock = QtDockWidget(
                    self.native,
                    widget.native,
                    name=name.replace("_", " "),
                    area=area,
                    allowed_areas=allowed_areas,
                )

                self.native.addDockWidget(QtDockWidget.areas[area], dock)
                if isinstance(widget, BaseGui):
                    widget.__magicclass_parent__ = self
                    self.__magicclass_children__.append(widget)
                    widget._my_symbol = Symbol(name)

            @nogui
            def remove_dock_widget(self: cls, widget: Widget):
                from ._dock_widget import QtDockWidget

                dock = None
                i_dock = -1
                for i, child in enumerate(self.__magicclass_children__):
                    if child is widget:
                        dock = child.native.parent()
                        if not isinstance(dock, QtDockWidget):
                            dock = None
                        i_dock = i
                        self.__magicclass_parent__ = None
                        break
                else:
                    raise RuntimeError("Dock widget not found.")

                self.native.removeDockWidget(dock)
                self.__magicclass_children__.pop(i_dock)

            @property
            def status(self: cls) -> str:
                """Get status tip."""
                return self.native.statusTip()

            @status.setter
            def status(self: cls, text: str):
                """Set status tip."""
                self.native.setStatusTip(text)
                self.native.statusBar().showMessage(text, 5000)

            cls.add_dock_widget = add_dock_widget
            cls.remove_dock_widget = remove_dock_widget
            cls.status = status

        cls.__init__ = __init__
        cls.__setattr__ = __setattr__
        cls.insert = insert
        cls.show = show
        cls.reset_choices = reset_choices
        cls.close = close
        cls._container_widget = container
        cls._remove_child_margins = no_margin
        return cls

    return wrapper


@make_gui(Container)
class ClassGui:
    pass


@make_gui(SplitterContainer)
class SplitClassGui:
    pass


@make_gui(ScrollableContainer)
class ScrollableClassGui:
    pass


@make_gui(DraggableContainer)
class DraggableClassGui:
    pass


@make_gui(CollapsibleContainer)
class CollapsibleClassGui:
    pass


@make_gui(HCollapsibleContainer)
class HCollapsibleClassGui:
    pass


@make_gui(ButtonContainer)
class ButtonClassGui:
    pass


@make_gui(ToolBoxContainer, no_margin=False)
class ToolBoxClassGui:
    pass


@make_gui(TabbedContainer, no_margin=False)
class TabbedClassGui:
    pass


@make_gui(StackedContainer, no_margin=False)
class StackedClassGui:
    pass


@make_gui(ListContainer, no_margin=False)
class ListClassGui:
    pass


@make_gui(SubWindowsContainer, no_margin=False)
class SubWindowsClassGui:
    pass


@make_gui(GroupBoxContainer, no_margin=False)
class GroupBoxClassGui:
    pass


@make_gui(FrameContainer, no_margin=False)
class FrameClassGui:
    pass


@make_gui(MainWindow)
class MainWindowClassGui:
    pass
