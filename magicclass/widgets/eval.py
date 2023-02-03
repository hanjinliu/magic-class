from __future__ import annotations
from functools import lru_cache

import sys
import re

from typing import Any, Mapping

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal
from magicgui.backends._qtpy.widgets import QBaseStringWidget
from magicclass._magicgui_compat import ValueWidget
import builtins


@lru_cache(maxsize=1)
def builtin_ns() -> list[str]:
    return {k: v for k, v in builtins.__dict__.items() if not k.startswith("_")}


_WordPattern = re.compile(
    r"[0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_\.]+"
)


class QCompletionPopup(QtW.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.itemClicked.connect(self._on_item_clicked)
        self.setFixedWidth(100)

    def parentWidget(self) -> QEvalLineEdit:
        return super().parentWidget()

    def _on_item_clicked(self, item: QtW.QListWidgetItem):
        self.parentWidget().setText(item.text())
        self.parentWidget().setFocus()
        self.close()

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        self.parentWidget().setFocus()

    def setNext(self):
        self.setCurrentRow((self.currentRow() + 1) % self.count())

    def setPrevious(self):
        self.setCurrentRow((self.currentRow() - 1) % self.count())


class LazyAttrGetter(Mapping[str, Any]):
    def __init__(self, obj):
        self._obj = obj
        self._attrs = dir(obj)

    def __getitem__(self, __key: str) -> Any:
        try:
            return getattr(self._obj, __key)
        except AttributeError:
            raise KeyError(__key) from None

    def __len__(self) -> int:
        return len(self._attrs)

    def __iter__(self) -> iter[str]:
        return iter(self._attrs)


class QEvalLineEdit(QtW.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self._on_text_changed)
        self._namespace: Mapping[str, Any] = {}
        if sys.platform == "win32":
            _font = "Consolas"
        elif sys.platform == "darwin":
            _font = "Menlo"
        else:
            _font = "Monospace"
        self.setFont(QtGui.QFont(_font))
        self._current_completion_state: tuple[str, list[str]] = None
        self._list_widget = None

    def namespace(self) -> dict[str, Any]:
        return self._namespace

    def setNamespace(self, ns: Mapping[str, Any]):
        self._namespace = dict(builtin_ns(), **ns)

    def _update_completion_state(self, allow_auto: bool) -> bool:
        self._current_completion_state = self._get_completion_list(self.text())
        if len(self._current_completion_state[1]) == 0:
            return False
        if len(self._current_completion_state[1]) == 1 and allow_auto:
            self._complete_with(self._current_completion_state[1][0])
        return True

    def show_completion(self, allow_auto: bool = True):
        if self._list_widget is not None:
            self._list_widget.setNext()
            return
        if not self._update_completion_state(allow_auto):
            return

        list_widget = QCompletionPopup()
        list_widget.setParent(self, Qt.WindowType.ToolTip)
        list_widget.addItems(self._current_completion_state[1])
        list_widget.move(self.mapToGlobal(self.cursorRect().bottomRight()))
        list_widget.show()
        self._list_widget = list_widget
        self._list_widget.setCurrentRow(0)
        self.setFocus()

    def _get_completion_list(self, text: str) -> tuple[str, list[str]]:
        found = _WordPattern.findall(text.split(" ")[-1])
        ns = self._namespace
        if len(found) == 0:
            return "", list(ns.keys())
        last_found: str = found[-1]
        *strs, last = last_found.split(".")
        if len(strs) == 0:
            return last, [k for k in ns.keys() if k.startswith(last_found)]
        else:
            for head in strs:
                val = ns.get(head, None)
                if val is None:
                    return last, []
                try:
                    ns = LazyAttrGetter(val)
                except Exception:
                    return last, []

            if last == "":
                return last, [k for k in ns if not k.startswith("_")]
            return last, [k for k in ns if k.startswith(last)]

    def _on_text_changed(self, text: str):
        if self._list_widget is not None:
            self._update_completion_state(allow_auto=False)
            self._list_widget.clear()
            self._list_widget.addItems(self._current_completion_state[1])
            self._list_widget.move(self.mapToGlobal(self.cursorRect().bottomLeft()))

    def _complete_with(self, comp: str):
        text = self.text()
        if self._current_completion_state is None:
            return
        _n = len(self._current_completion_state[0])
        self.setText(text + comp[_n:])
        if self._list_widget is not None:
            self._list_widget.close()
            self._list_widget = None

    def event(self, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            event = QtGui.QKeyEvent(event)
            if event.key() == Qt.Key.Key_Tab:
                self.show_completion()
                return True
            elif event.key() == Qt.Key.Key_Down:
                if self._list_widget is not None:
                    self._list_widget.setNext()
                    return True
            elif event.key() == Qt.Key.Key_Up:
                if self._list_widget is not None:
                    self._list_widget.setPrevious()
                    return True
            elif event.key() == Qt.Key.Key_Return:
                if self._list_widget is not None:
                    comp = self._list_widget.currentItem().text()
                    self._complete_with(comp)
                    return True
            elif event.key() == Qt.Key.Key_Escape:
                if self._list_widget is not None:
                    self._list_widget.deleteLater()
                    self._list_widget = None
                    return True
        return super().event(event)

    def focusOutEvent(self, a0: QtGui.QFocusEvent) -> None:
        if self._list_widget is not None:
            self._list_widget.close()
            self._list_widget = None
        return super().focusOutEvent(a0)


class _EvalLineEdit(QBaseStringWidget):
    _qwidget: QEvalLineEdit

    def __init__(self, **kwargs):
        super().__init__(QEvalLineEdit, "text", "setText", "textChanged", **kwargs)

    def _post_get_hook(self, value):
        return eval(value, self._qwidget.namespace(), {})


class EvalLineEdit(ValueWidget):
    def __init__(self, namespace: Mapping[str, Any] = {}, **kwargs):
        kwargs["widget_type"] = _EvalLineEdit
        super().__init__(
            # backend_kwargs={"qwidg": QEvalLineEdit},
            **kwargs,
        )
        self.native: QEvalLineEdit
        self.native.setNamespace(namespace)

    @property
    def namespace(self):
        return self.native.namespace()
