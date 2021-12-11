from __future__ import annotations
from magicgui.widgets import FunctionGui, Image
from magicgui.widgets._bases.widget import Widget
import numpy as np

import qtpy
from qtpy.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QSplitter, QTextEdit
from qtpy.QtCore import Qt
from typing import Any, Callable, Iterator

from .gui.mgui_ext import Action, PushButtonPlus, WidgetAction
from .gui._base import MagicTemplate
from .gui.class_gui import CollapsibleClassGui, ScrollableClassGui, ButtonClassGui
from .utils import iter_members, extract_tooltip, get_signature

class HelpWidget(QSplitter):
    def __init__(self, ui=None, parent=None) -> None:
        super().__init__(orientation=Qt.Horizontal, parent=parent)
        self._tree = QTreeWidget(self)
        self._tree.itemClicked.connect(self._on_treeitem_clicked)
        self._tree.invisibleRootItem().setText(0, "")
        self._text = QTextEdit(self)
        self._text.setReadOnly(True)
        self._mgui_image = Image()
        self._mgui_image.min_height = 240
        
        self._image_and_text = QSplitter(orientation=Qt.Vertical, parent=self)
        self._image_and_text.insertWidget(0, self._mgui_image.native)
        self._image_and_text.insertWidget(1, self._text)
        
        self.insertWidget(0, self._tree)
        self.insertWidget(1, self._image_and_text)
        
        if ui is not None:
            self.set_tree(ui)
            self.update_ui(ui)
            
        width = self.width()
        left_width = width//3
        self.setSizes([left_width, width - left_width])
    
    def set_tree(self, ui: MagicTemplate, root: UiBoundTreeItem = None):
        if root is None:
            root = UiBoundTreeItem(self._tree, ui)
            root.setText(0, ui.name)
            self._tree.invisibleRootItem().addChild(root)
        
        for i, widget in enumerate(_iter_unwrapped_children(ui)):
            if isinstance(widget, MagicTemplate):
                child = UiBoundTreeItem(root, ui=widget)
                self.set_tree(widget, root=child)
            else:
                child = UiBoundTreeItem(root, ui=None)
            child.setText(0, f"({i+1}) {widget.name}")
            root.addChild(child)
    
    def update_ui(self, ui: MagicTemplate):
        img, docs = get_help_info(ui)
        
        # set image
        self._mgui_image.value = img
        
        # set text
        self._text.clear()
        htmls = ["<br><h1>Contents</h1>"]
        
        for i, (name, doc) in enumerate(docs.items()):
            htmls.append(f"<h2>({i+1}) {name}</h2><p>{doc}</p>")
        self._text.insertHtml("<br>".join(htmls))

    def _on_treeitem_clicked(self, item: UiBoundTreeItem, i: int):
        if item.ui is not None:
            self.update_ui(item.ui)
            item.setExpanded(True)

    
class UiBoundTreeItem(QTreeWidgetItem):
    def __init__(self, parent, ui=None):
        super().__init__(parent)
        self.ui = ui
    

def _issubclass(child: Any, parent: Any):
    try:
        return issubclass(child, parent)
    except TypeError:
        return False

def get_keymap(ui: MagicTemplate | type[MagicTemplate]):
    from .signature import get_additional_option
    from .gui.keybinding import as_shortcut
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
                keymap[keystr] = (name, extract_tooltip(attr))
                
    return keymap

def get_help_info(ui: MagicTemplate) -> tuple[np.ndarray, dict[str, str]]:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    backend = mpl.get_backend()
    try:
        if isinstance(ui, (ScrollableClassGui, ButtonClassGui, CollapsibleClassGui)):
            # TODO: collapsed GUI
            img = _render(ui._widget._inner_widget)
        else:
            img = ui.render()
        scale = _screen_scale()
        docs: dict[str, str] = {}
        mpl.use("Agg")
        with plt.style.context("default"):
            fig, ax = plt.subplots(1, 1)
            ax.axis("off")
            ax.imshow(img)
            for i, widget in enumerate(_iter_unwrapped_children(ui)):
                pos = widget.native.mapToParent(widget.native.rect().topLeft())
                ax.text(pos.x() * scale, pos.y() * scale, f"({i+1})",
                        ha="center", va="center", color="white", size="x-large",
                        backgroundcolor="black", fontfamily="Arial")
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
        doc = widget.__doc__
    elif isinstance(widget, (Action, PushButtonPlus)):
        doc = widget._doc
    elif isinstance(widget, FunctionGui):
        doc = widget._function.__doc__
    elif isinstance(widget, (Widget, WidgetAction)):
        doc = widget.tooltip
    else:
        raise TypeError(type(widget))
    from magicgui.widgets._function_gui import _docstring_to_html
    return _docstring_to_html(doc)

def _render(qwidget: QWidget):
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
    for widget in ui:
        if not getattr(widget, "_unwrapped", False):
            yield widget