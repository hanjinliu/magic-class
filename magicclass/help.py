from __future__ import annotations
import weakref

from magicgui.widgets import FunctionGui, Image
from magicgui.widgets._bases.widget import Widget
from magicgui.widgets._function_gui import _docstring_to_html

import qtpy
from qtpy.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QSplitter
from qtpy.QtCore import Qt
from typing import Any, Callable, Iterator, TYPE_CHECKING

from .widgets.containers import SplitterContainer
from .widgets.misc import ConsoleTextEdit

from ._gui.mgui_ext import Action, PushButtonPlus, WidgetAction
from ._gui._base import MagicTemplate
from .widgets import DraggableContainer, FreeWidget, Separator
from ._gui.class_gui import (
    CollapsibleClassGui,
    DraggableClassGui,
    ScrollableClassGui,
    ButtonClassGui,
)
from .utils import iter_members, Tooltips, get_signature

if TYPE_CHECKING:
    import numpy as np

# TODO: find, key-binding


class _HelpWidget(QSplitter):
    """
    A Qt widget that will show information of a magic-class widget, built from its
    class structure, function docstrings and type annotations.
    """

    _initial_image_size = 250

    def __init__(self, ui=None, parent=None) -> None:
        super().__init__(orientation=Qt.Horizontal, parent=parent)
        self.setWindowFlag(Qt.Window)
        self._tree = QTreeWidget(self)
        self._tree.itemClicked.connect(self._on_treeitem_clicked)
        self._text = ConsoleTextEdit()
        self._text.read_only = True
        self._mgui_image = Image()
        c = DraggableContainer(widgets=[self._mgui_image])

        def wheelEvent(event):
            ang = event.angleDelta().y()
            v0 = self._mgui_image.min_height
            if ang > 0:
                v = v0 * 1.1
            else:
                v = v0 / 1.1
            self._resize_image(int(v))

        self._mgui_image.native.wheelEvent = wheelEvent

        c.min_height = 120
        self._resize_image(self._initial_image_size)

        widget_right = SplitterContainer(widgets=[c, self._text])

        self.insertWidget(0, self._tree)
        self.insertWidget(1, widget_right.native)

        if ui is not None:
            self.set_tree(ui)
            self._update_ui_view(ui)

        width = self.width()
        left_width = width // 3
        self.setSizes([left_width, width - left_width])

    def set_tree(self, ui: MagicTemplate, root: UiBoundTreeItem = None):
        name = ui.name
        if root is None:
            root = UiBoundTreeItem(self._tree, ui)
            root.setText(0, name)
            root.setExpanded(True)
            self._tree.invisibleRootItem().addChild(root)

        for i, widget in enumerate(_iter_unwrapped_children(ui)):
            if isinstance(widget, MagicTemplate):
                child = UiBoundTreeItem(root, ui=widget)
                self.set_tree(widget, root=child)
                if child.childCount() == 1 and isinstance(
                    child.child(0).ui, MagicTemplate
                ):
                    # If only one magic class is nested, we don't create redundant items
                    grandchild = child.takeChild(0)
                    grandchild.setText(
                        0, f"({i+1}) {widget.name} > {grandchild.ui.name}"
                    )
                    root.removeChild(child)
                    child = grandchild
                else:
                    child.setText(0, f"({i+1}) {widget.name}")

            else:
                if isinstance(getattr(widget, "_inner_widget", widget), Separator):
                    # separator does not need a help
                    continue
                child = UiBoundTreeItem(root, ui=None)
                child.setText(0, f"({i+1}) {widget.name}")

            root.addChild(child)

    def _resize_image(self, v: float):
        self._mgui_image.min_height = v
        self._mgui_image.max_height = v
        self._mgui_image.min_width = v
        self._mgui_image.max_width = v

    def _update_ui_view(self, ui: MagicTemplate):
        img, docs = get_help_info(ui)

        # set image
        self._mgui_image.value = img

        # set text
        htmls = [f"<h1>{ui.name}</h1><p>{Tooltips(ui).desc}</p>"]

        if docs:
            htmls.append("<h2>Contents</h2>")

        for i, (name, doc) in enumerate(docs.items()):
            htmls.append(f"<h3>({i+1}) {name}</h3><p>{doc}</p>")
        self._text.value = "".join(htmls)

    def _on_treeitem_clicked(self, item: UiBoundTreeItem, i: int = 0):
        if item.ui is not None:
            self._update_ui_view(item.ui)
            item.setExpanded(True)
        else:
            self._on_treeitem_clicked(item.parent())
        self._resize_image(self._initial_image_size)


class UiBoundTreeItem(QTreeWidgetItem):
    def __init__(self, parent, ui=None):
        super().__init__(parent)
        if ui is not None:
            self._ui = weakref.ref(ui)
        else:
            self._ui = None

    @property
    def ui(self):
        if self._ui is None:
            return None
        return self._ui()

    def child(self, index: int) -> UiBoundTreeItem:
        # Just for typing
        return super().child(index)

    def takeChild(self, index: int) -> UiBoundTreeItem:
        # Just for typing
        return super().takeChild(index)


class HelpWidget(FreeWidget):
    def __init__(self, ui=None, parent=None):
        super().__init__()
        self._help_widget = _HelpWidget(ui, parent)
        self.set_widget(self._help_widget)
        self.native.setWindowTitle("Help")


def _issubclass(child: Any, parent: Any):
    try:
        return issubclass(child, parent)
    except TypeError:
        return False


def get_help_info(ui: MagicTemplate) -> tuple[np.ndarray, dict[str, str]]:
    import numpy as np
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    backend = mpl.get_backend()
    try:
        _has_inner_widget = (
            ScrollableClassGui,
            DraggableClassGui,
            CollapsibleClassGui,
            ButtonClassGui,
        )
        if isinstance(ui, _has_inner_widget):
            inner_widget = ui._widget._inner_widget
            visible = inner_widget.isVisible()
            inner_widget.setVisible(True)
            img = _render(inner_widget)
            inner_widget.setVisible(visible)
        # elif isinstance(ui, TabbedClassGui):
        # TODO: Cannot assign correct position of tabs now.
        else:
            img = ui.render()
        scale = _screen_scale()
        docs: dict[str, str] = {}
        mpl.use("Agg")
        with plt.style.context("default"):
            fig, ax = plt.subplots(1, 1)
            ax.axis("off")
            fig.patch.set_alpha(0.05)
            ax.imshow(img)
            for i, widget in enumerate(_iter_unwrapped_children(ui)):
                x, y = _get_relative_pos(widget)
                if x >= 0 and y >= 0:
                    ax.text(
                        x * scale,
                        y * scale,
                        f"({i+1})",
                        ha="center",
                        va="center",
                        color="white",
                        backgroundcolor="black",
                        fontfamily="Arial",
                    )
                docs[widget.name] = _get_doc(widget)
            fig.tight_layout()
            fig.canvas.draw()

            data = np.asarray(fig.canvas.renderer.buffer_rgba(), dtype=np.uint8)

    finally:
        mpl.use(backend)

    return data, docs


def _screen_scale() -> float:
    from qtpy.QtGui import QGuiApplication

    screen = QGuiApplication.screens()[0]
    return screen.devicePixelRatio()


def _get_doc(widget) -> str:
    if isinstance(widget, MagicTemplate):
        doc = widget.__doc__ or ""
    elif isinstance(widget, (Action, PushButtonPlus)):
        doc = _docstring_to_html(widget._doc)
    elif isinstance(widget, FunctionGui):
        doc = _docstring_to_html(widget._function.__doc__)
    elif isinstance(widget, (Widget, WidgetAction)):
        doc = widget.tooltip or ""
    else:
        raise TypeError(type(widget))
    doc = doc.rstrip("<h3>Parameters</h3><ul></ul>")  # If parameter info was not given
    if doc == "":
        doc = "(No document found)"
    return doc


def _render(qwidget: QWidget) -> np.ndarray:
    """Render Qt widgets. Used in certain type of containers."""
    import numpy as np

    img = qwidget.grab().toImage()
    bits = img.constBits()
    h, w, c = img.height(), img.width(), 4
    if qtpy.API_NAME == "PySide2":
        arr = np.array(bits).reshape(h, w, c)
    else:
        bits.setsize(h * w * c)
        arr = np.frombuffer(bits, np.uint8).reshape(h, w, c)

    return arr[:, :, [2, 1, 0, 3]]


def _iter_unwrapped_children(ui: MagicTemplate) -> Iterator[Widget]:
    all_widgets: set[Widget] = set()

    for item in ui._list:
        widget = getattr(item, "_inner_widget", item)
        all_widgets.add(widget)
    for widget in ui.__magicclass_children__:
        all_widgets.add(widget)

    for w in all_widgets:
        if not getattr(w, "_unwrapped", False):
            yield w


def _get_relative_pos(widget: Widget) -> tuple[int, int]:
    """Get relative position of a widget seen from its parent."""
    if hasattr(widget, "_labeled_widget"):
        w = widget._labeled_widget()
        if w is None:
            w = widget
        try:
            qpos = w.native.mapToParent(w.native.rect().topLeft())
            out = qpos.x(), qpos.y()
        except Exception:
            out = (-1, -1)
    else:
        out = (-1, -1)
    return out


def get_keymap(ui: MagicTemplate | type[MagicTemplate]):
    from .signature import get_additional_option
    from ._gui.keybinding import as_shortcut

    keymap: dict[str, Callable] = {}

    if isinstance(ui, MagicTemplate):
        cls = ui.__class__
    elif _issubclass(ui, MagicTemplate):
        cls = ui
    else:
        raise TypeError("'get_keymap' can only be called with MagicTemplate input.")

    for name, attr in iter_members(cls, exclude_prefix=" "):
        if isinstance(attr, type) and issubclass(attr, MagicTemplate):
            child_keymap = get_keymap(attr)
            keymap.update(child_keymap)
        else:
            kb = get_additional_option(attr, "keybinding", None)
            if kb:
                keystr = as_shortcut(kb).toString()
                keymap[keystr] = (name, Tooltips(attr).desc)

    return keymap
