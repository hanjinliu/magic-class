from __future__ import annotations
from typing import Any, Callable, Sequence, TypeVar
import warnings
from psygnal import Signal
from qtpy.QtWidgets import QMenuBar, QWidget, QMainWindow, QBoxLayout, QDockWidget
from qtpy.QtCore import Qt
from magicgui.application import use_app
from magicgui.widgets import (
    Container,
    MainWindow,
    Label,
    FunctionGui,
    Image,
    Table,
    Widget,
    EmptyWidget,
)
from magicgui.widgets.bases import (
    ButtonWidget,
    ValueWidget,
    ContainerWidget,
)
from magicgui.types import Undefined
from magicgui.widgets._concrete import _LabeledWidget
from macrokit import Symbol

from .keybinding import register_shortcut
from .mgui_ext import PushButtonPlus
from .toolbar import ToolBarGui, QtTabToolBar
from .menu_gui import MenuGui, ContextMenuGui
from ._base import (
    BaseGui,
    PopUpMode,
    ErrorMode,
    normalize_insertion,
)
from .utils import format_error, connect_magicclasses
from ._macro_utils import value_widget_callback
from magicclass.widgets import (
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
    ResizableContainer,
    ToolBoxContainer,
    FreeWidget,
)
from magicclass.widgets._box import Box
from magicclass.box._fields import BoxMagicField

from magicclass.utils import iter_members, Tooltips
from magicclass.fields import MagicField
from magicclass.signature import get_additional_option
from magicclass._app import run_app

# For Containers that belong to these classes, menubar must be set to _qwidget.layout().
_USE_OUTER_LAYOUT = (
    ScrollableContainer,
    DraggableContainer,
    SplitterContainer,
    TabbedContainer,
    SubWindowsContainer,
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
                f"MagicField {name} does not contain enough information for widget "
                "creation."
            )

        fld.name = fld.name or name
        widget = fld.get_widget(self)

        if isinstance(widget, (ValueWidget, ContainerWidget)):
            # If the field has callbacks, connect it to the newly generated widget.
            if fld.record:
                getvalue = type(fld) in (MagicField, BoxMagicField)
                if isinstance(widget, ValueWidget):
                    if widget._bound_value is Undefined:
                        f = value_widget_callback(self, widget, name, getvalue=getvalue)
                        widget.changed.connect(f)
                elif hasattr(widget, "value"):
                    f = value_widget_callback(self, widget, name, getvalue=getvalue)
                    widget.changed.connect(f)

        elif fld.callbacks:
            warnings.warn(
                f"{type(widget).__name__} does not have `changed` signal. "
                "Connecting callback functions does no effect.",
                UserWarning,
            )

        return widget

    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and
        nested classes are converted to magicgui widgets.
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
                widget = self._convert_an_attribute_into_widget(name, attr, _tooltips)

                if isinstance(widget, MenuGui):
                    # Add menubar to container
                    if self._menubar is None:
                        # if widget has no menubar, a new one should be created.
                        self._menubar = QMenuBar()
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
                                    "Cannot add menubar after adding a toolbar in a "
                                    "non-main window. Use maigcclass(widget_type="
                                    "'mainwindow') instead, or define the menu class "
                                    "before toolbar class."
                                )

                    widget.native.setParent(self._menubar, widget.native.windowFlags())
                    self._menubar.addMenu(widget.native).setText(
                        widget.name.replace("_", " ")
                    )
                    _hist.append((name, type(attr), "MenuGui"))

                elif isinstance(widget, ContextMenuGui):
                    # Add context menu to container
                    widget._set_magic_context_menu(self)
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
                                    0,
                                    self._toolbar,
                                    alignment=Qt.AlignmentFlag.AlignTop,
                                )
                                self._toolbar.setContentsMargins(0, 0, 0, 0)
                                # if not isinstance(self, _USE_OUTER_LAYOUT):
                                #     n_insert += 1

                    widget.native.setParent(self._toolbar, widget.native.windowFlags())
                    self._toolbar.addToolBar(
                        widget.native, widget.name.replace("_", " ")
                    )
                    _hist.append((name, type(attr), "ToolBarGui"))

                elif isinstance(widget, (Widget, Callable)):
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
                        try:
                            # Methods or any callable objects, but FunctionGui is not
                            # included.
                            # NOTE: Here any custom callable objects could be given.
                            # Some callable objects can be incompatible but useful.
                            # Those callable objects should be passed from widget
                            # construction.
                            widget = self._create_widget_from_method(widget)
                        except AttributeError as e:
                            warnings.warn(
                                f"Could not convert {widget!r} into a widget "
                                f"due to AttributeError: {e}",
                                UserWarning,
                            )
                            continue

                        # contextmenu
                        contextmenu = get_additional_option(attr, "context_menu", None)
                        if contextmenu is not None:
                            contextmenu: ContextMenuGui
                            contextmenu._set_magic_context_menu(widget)
                            connect_magicclasses(self, contextmenu, contextmenu.name)

                    elif hasattr(widget, _MCLS_PAREMT) or hasattr(
                        widget.__class__, _MCLS_PAREMT
                    ):
                        # magic-class has to know its parent.
                        # if __magicclass_parent__ is defined as a property, hasattr
                        # must be called with a type object (not instance).
                        widget.__magicclass_parent__ = self

                    else:
                        if not widget.name:
                            widget.name = name
                        if hasattr(widget, "text") and not widget.text:
                            widget.text = widget.name.replace("_", " ")

                    # Now, "widget" is a Widget object. Add widget in a way similar to
                    # "insert" method of Container.
                    if widget.name.startswith("_"):
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

    def _fast_insert(
        self, key: int, obj: Widget | Callable, remove_label: bool = False
    ) -> None:
        widget = normalize_insertion(self, obj)

        if isinstance(widget, (ValueWidget, ContainerWidget)):
            widget.changed.connect(lambda: self.changed.emit(self))

        if hasattr(widget, _MCLS_PAREMT) or hasattr(widget.__class__, _MCLS_PAREMT):
            widget.__magicclass_parent__ = self
            if isinstance(widget, ClassGuiBase):
                if self._remove_child_margins:
                    widget.margins = (0, 0, 0, 0)
                if widget not in self.__magicclass_children__:
                    # nested magic classes are already in the list
                    self.__magicclass_children__.add(widget)
                    widget._my_symbol = Symbol(widget.name)

        _widget = widget
        if isinstance(widget, Box):
            widget = widget.widget

        if self.labels:
            # no labels for button widgets (push buttons, checkboxes, have their own)
            if not isinstance(widget, _HIDE_LABELS) and not remove_label:
                _widget = _LabeledWidget(_widget)
                widget.label_changed.connect(self._unify_label_widths)

        if key < 0:
            key += len(self)
        self._list.insert(key, widget)
        if remove_label:
            _widget = EmptyWidget(visible=False)
        self._widget._mgui_insert_widget(key, _widget)

        # NOTE: Function GUI is invisible by some reason...
        # See https://github.com/hanjinliu/magic-class/issues/53
        if isinstance(widget, FunctionGui):
            widget.visible = True
        return None

    def insert(self, key: int, widget: Widget) -> None:
        """Insert widget at the give position."""
        self._fast_insert(key, widget)
        self._unify_label_widths()
        return None

    def __setattr__(self, name: str, value: Any) -> None:
        if not isinstance(getattr(self.__class__, name, None), MagicField):
            Container.__setattr__(self, name, value)
        else:
            object.__setattr__(self, name, value)

    def reset_choices(self, *_: Any):
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

    def show(self, run: bool = True) -> None:
        """
        Show GUI. If any of the parent GUI is a dock widget in napari, then this
        will also show up as a dock widget (floating if in popup mode).

        Parameters
        ----------
        run : bool, default True
            If true, application gets executed.
        """
        mcls_parent = self.__magicclass_parent__
        qt_parent = self.native.parent()
        if mcls_parent is not None and qt_parent is None:
            # If child magic class is closed before, we have to set parent again.
            self.native.setParent(mcls_parent.native, self.native.windowFlags())
            qt_parent = self.native.parent()

        viewer = self.parent_viewer
        if viewer is not None and qt_parent is not None:
            _dock_found = False
            if isinstance(qt_parent, QDockWidget):
                for dock in viewer.window._dock_widgets.values():
                    if dock is qt_parent:
                        _dock_found = True
                        dock.show()
                        break
            if not _dock_found:
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
            Container.show(self, run=False)
            if mcls_parent is not None:
                topleft = mcls_parent.native.geometry().topLeft()
                topleft.setX(topleft.x() + 20)
                topleft.setY(topleft.y() + 20)
                self.native.move(topleft)
            self.native.activateWindow()
            if run:
                run_app()
        return None

    def close(self):
        """Close GUI. if this widget is a dock widget, then also close it."""

        current_self = self._search_parent_magicclass()
        viewer = current_self.parent_viewer
        qt_parent = self.native.parent()
        if viewer is not None and isinstance(qt_parent, QDockWidget):
            try:
                viewer.window.remove_dock_widget(qt_parent)
            except Exception:
                pass

        Container.close(self)

        return None

    def _unify_label_widths(self):
        if not self._initialized:
            return

        need_labels = [w for w in self._list if not isinstance(w, _HIDE_LABELS)]
        if self.layout == "vertical" and self.labels and need_labels:
            measure = use_app().get_obj("get_text_width")
            widest_label = max(measure(w.label) for w in need_labels)
            for w in self:
                labeled_widget = w._labeled_widget()
                if labeled_widget:
                    labeled_widget.label_width = widest_label


_HIDE_LABELS = (
    _LabeledWidget,
    ButtonWidget,
    ClassGuiBase,
    FreeWidget,
    Label,
    Image,
    Table,
    FunctionGui,
)


def find_window_ancestor(widget: Widget) -> SubWindowsClassGui:
    """
    Try to find a window ancestor of the given widget.

    This function is used only for subwindows.
    """
    parent_self = widget
    while (parent := getattr(parent_self, "__magicclass_parent__", None)) is not None:
        parent_self = parent
        if isinstance(parent_self, SubWindowsClassGui):
            break

    if not isinstance(parent_self, SubWindowsClassGui):
        raise RuntimeError(
            "Could not find GUI class that support sub-windows. Please use\n"
            ">>> @magicclass(widget_type='subwindows')\n"
            "to create main window widget."
        )
    return parent_self


_C = TypeVar("_C", bound=ContainerWidget)
_C2 = TypeVar("_C2")


def make_gui(
    container: type[_C], no_margin: bool = True
) -> Callable[[_C2], type[_C | _C2 | ClassGuiBase]]:
    """
    Make a ClassGui class from a Container widget.

    Because GUI class inherits Container here, functions that need overriden must be
    defined here, not in ClassGuiBase.
    """

    def wrapper(cls_: type[ClassGuiBase]):
        cls: type[_C | ClassGuiBase] = type(
            cls_.__name__, (container, ClassGuiBase), {}
        )

        def __init__(
            self: ClassGuiBase,
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
            self.native.setWindowTitle(self.name.replace("_", " ").strip())

        close = ClassGuiBase.close

        if issubclass(container, MainWindow):
            # Similar to napari's viewer.window.add_dock_widget.
            # See napari/_qt/widgets/qt_viewer_dock_widget.py
            from magicclass.wrappers import nogui

            # This function will be detected as non-reserved method so that magicclass
            # will try to convert it into widget. Should decorate with @nogui.
            @nogui
            def add_dock_widget(
                self: MainWindowClassGui,
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
                    Widget that will be converted into a dock widget and added to the
                    main window.
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
                    self.__magicclass_children__.add(widget)
                    widget._my_symbol = Symbol(name)

            @nogui
            def remove_dock_widget(self: MainWindowClassGui, widget: Widget):
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

            def close(self: MainWindowClassGui):
                """Close GUI."""
                self.native.close()
                return None

            @property
            def status(self: MainWindowClassGui) -> str:
                """Get status tip."""
                return self.native.statusTip()

            @status.setter
            def status(self: MainWindowClassGui, text: str):
                """Set status tip."""
                self.native.setStatusTip(text)
                self.native.statusBar().showMessage(text, 5000)

            cls.add_dock_widget = add_dock_widget
            cls.remove_dock_widget = remove_dock_widget
            cls.status = status

        cls.__init__ = __init__
        cls.__delitem__ = container.__delitem__
        cls.__iter__ = container.__iter__
        cls.__len__ = container.__len__
        cls.__dir__ = ClassGuiBase.__dir__
        cls._unify_label_widths = ClassGuiBase._unify_label_widths
        cls.__setattr__ = ClassGuiBase.__setattr__
        cls.insert = ClassGuiBase.insert
        cls.show = ClassGuiBase.show
        cls.reset_choices = ClassGuiBase.reset_choices
        cls.close = close
        cls._container_widget = container
        cls._remove_child_margins = no_margin
        return cls

    return wrapper


# fmt: off
@make_gui(Container)
class ClassGui: pass  # noqa: E701
@make_gui(SplitterContainer)
class SplitClassGui: pass  # noqa: E701
@make_gui(ScrollableContainer)
class ScrollableClassGui: pass  # noqa: E701
@make_gui(DraggableContainer)
class DraggableClassGui: pass  # noqa: E701
@make_gui(CollapsibleContainer)
class CollapsibleClassGui: pass  # noqa: E701
@make_gui(HCollapsibleContainer)
class HCollapsibleClassGui: pass  # noqa: E701
@make_gui(ButtonContainer)
class ButtonClassGui: pass  # noqa: E701
@make_gui(ToolBoxContainer, no_margin=False)
class ToolBoxClassGui: pass  # noqa: E701
@make_gui(TabbedContainer, no_margin=False)
class TabbedClassGui: pass  # noqa: E701
@make_gui(StackedContainer, no_margin=False)
class StackedClassGui: pass  # noqa: E701
@make_gui(ListContainer, no_margin=False)
class ListClassGui: pass  # noqa: E701
@make_gui(SubWindowsContainer, no_margin=False)
class SubWindowsClassGui: pass  # noqa: E701
@make_gui(GroupBoxContainer, no_margin=False)
class GroupBoxClassGui: pass  # noqa: E701
@make_gui(FrameContainer, no_margin=False)
class FrameClassGui: pass  # noqa: E701
@make_gui(ResizableContainer, no_margin=False)
class ResizableClassGui: pass  # noqa: E701
@make_gui(MainWindow)
class MainWindowClassGui: pass  # noqa: E701
# fmt: on
