from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping
from collections import Counter

from macrokit import parse, Head, Expr
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from magicgui.backends._qtpy.widgets import QBaseStringWidget
from magicgui.widgets.bases import ValueWidget
from magicclass.widgets._const import FONT


def _get_last_group(text: str) -> str | None:
    if text.endswith(" "):
        # look for the global namespace
        return ""

    _ends_with_dot = text.endswith(".")
    if _ends_with_dot:
        text = text[:-1]

    # check unmatched brackets
    counter = Counter(text)
    for left, right in ["()", "[]", "{}"]:
        if counter[left] > counter[right]:
            _n_left = 0
            for i in range(1, len(text) + 1):
                c = text[-i]
                if c == left:
                    _n_left += 1
                elif c == right:
                    _n_left -= 1
                if _n_left > 0:
                    break
            text = text[-i + 1 :]

    try:
        mk_expr = parse(text)
    except Exception:
        return None

    while isinstance(mk_expr, Expr) and mk_expr.head in (Head.binop, Head.unop):
        mk_expr = mk_expr.args[-1]
    last_found = str(mk_expr)
    if _ends_with_dot:
        last_found += "."
    return last_found


class QCompletionPopup(QtW.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.itemClicked.connect(self._on_item_clicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def parentWidget(self) -> QEvalLineEdit:
        return super().parentWidget()

    def resizeForContents(self):
        self.setFixedSize(
            self.sizeHintForColumn(0) + self.frameWidth() * 2,
            min(self.sizeHintForRow(0) * self.count() + self.frameWidth() * 2, 200),
        )

    def _on_item_clicked(self, item: QtW.QListWidgetItem):
        self.parentWidget()._complete_with_current_item()

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        self.parentWidget().setFocus()

    def setNext(self):
        self.setCurrentRow((self.currentRow() + 1) % self.count())

    def setNextPage(self):
        h0 = self.sizeHintForRow(0)
        self.setCurrentRow(
            min(self.currentRow() + self.height() // h0, self.count() - 1)
        )

    def setLast(self):
        self.setCurrentRow(self.count() - 1)

    def setPrevious(self):
        self.setCurrentRow((self.currentRow() - 1) % self.count())

    def setPreviousPage(self):
        h0 = self.sizeHintForRow(0)
        self.setCurrentRow(max(self.currentRow() - self.height() // h0, 0))

    def setFirst(self):
        self.setCurrentRow(0)


class QEvalLineEdit(QtW.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self._on_text_changed)
        self._namespace: Mapping[str, Any] = {}
        self.setFont(QtGui.QFont(FONT))
        self._current_completion_state: tuple[str, list[str]] = None
        self._list_widget = None
        self._auto_suggest = True

    def namespace(self) -> dict[str, Any]:
        return self._namespace

    def setNamespace(self, ns: Mapping[str, Any]):
        self._namespace = dict(ns)
        self._namespace["__builtins__"] = {}  # for safety

    def setAutoSuggest(self, auto_suggest: bool):
        self._auto_suggest = auto_suggest

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
        self._create_list_widget()

    def _create_list_widget(self):
        list_widget = QCompletionPopup()
        list_widget.setParent(self, Qt.WindowType.ToolTip)
        list_widget.setFont(self.font())
        if self._current_completion_state is not None:
            items = self._current_completion_state[1]
            list_widget.addItems(items)
            if len(items) == 0:
                # don't show the list widget if there are no items
                return
        list_widget.resizeForContents()
        list_widget.move(self.mapToGlobal(self.cursorRect().bottomRight()))
        list_widget.show()
        self._list_widget = list_widget
        self._list_widget.setCurrentRow(0)
        self.setFocus()

    def _get_completion_list(self, text: str) -> tuple[str, list[str]]:
        last_found = _get_last_group(text)
        if last_found is None:
            return "", []

        ns = self._namespace
        if len(last_found) == 0:
            return "", list(k for k in ns.keys() if k != "__builtins__")
        *strs, last = last_found.split(".")
        if len(strs) == 0:
            return last, [
                k for k in ns.keys() if k.startswith(last_found) and k != "__builtins__"
            ]
        else:
            try:
                val = eval(".".join(strs), self.namespace(), {})
            except Exception:
                return last, []

            attrs = dir(val)

            if last == "":
                return last, sorted(
                    (k for k in attrs if not k.startswith("_")),
                    key=lambda x: x.swapcase(),
                )

            return last, sorted(
                (k for k in attrs if k.startswith(last)), key=lambda x: x.swapcase()
            )

    def _on_text_changed(self, text: str):
        if self._list_widget is None and self._auto_suggest:
            if not self._update_completion_state(False):
                return
            self._create_list_widget()
        if self._list_widget is not None:
            self._update_completion_state(allow_auto=False)
            self._list_widget.clear()
            items = self._current_completion_state[1]
            if len(items) == 0 or len(text) == 0:
                self._list_widget.close()
                self._list_widget = None
                return
            self._list_widget.addItems(items)
            self._list_widget.move(self.mapToGlobal(self.cursorRect().bottomLeft()))
            self._list_widget.resizeForContents()

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
            assert isinstance(event, QtGui.QKeyEvent)
            if event.key() == Qt.Key.Key_Tab:
                self.show_completion()
                return True
            elif event.key() == Qt.Key.Key_Down:
                if self._list_widget is not None:
                    if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                        self._list_widget.setNext()
                    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                        self._list_widget.setLast()
                    else:
                        return False
                    return True
            elif event.key() == Qt.Key.Key_PageDown:
                if self._list_widget is not None:
                    self._list_widget.setNextPage()
                    return True
            elif event.key() == Qt.Key.Key_Up:
                if self._list_widget is not None:
                    if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                        self._list_widget.setPrevious()
                    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                        self._list_widget.setFirst()
                    else:
                        return False
                    return True
            elif event.key() == Qt.Key.Key_PageUp:
                if self._list_widget is not None:
                    self._list_widget.setPreviousPage()
                    return True
            elif event.key() == Qt.Key.Key_Return:
                if self._list_widget is not None:
                    self._complete_with_current_item()
                    return True
            elif event.key() == Qt.Key.Key_Escape:
                if self._list_widget is not None:
                    self._list_widget.deleteLater()
                    self._list_widget = None
                    return True
        elif event.type() == QtCore.QEvent.Type.Move:
            if self._list_widget is not None:
                self._list_widget.close()
                self._list_widget = None
        return super().event(event)

    def _complete_with_current_item(self):
        comp = self._list_widget.currentItem().text()
        self._complete_with(comp)

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
        from magicclass.types import ExprStr

        return ExprStr(value, self._qwidget.namespace())


class EvalLineEdit(ValueWidget):
    def __init__(
        self, namespace: Mapping[str, Any] = {}, auto_suggest: bool = True, **kwargs
    ):
        kwargs["widget_type"] = _EvalLineEdit
        super().__init__(**kwargs)
        self.native: QEvalLineEdit
        self.native.setNamespace(namespace)

    @property
    def namespace(self):
        """Namespace of the eval line edit."""
        return MappingProxyType(self.native.namespace())

    @namespace.setter
    def namespace(self, ns: Mapping[str, Any]):
        """Set the namespace of the eval line edit."""
        self.native.setNamespace(ns)

    def eval(self):
        """Evaluate current text."""
        return eval(self.value, self.native.namespace(), {})
