from __future__ import annotations
from typing import Any, Callable, Union
from psygnal import Signal

from qtpy import QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal as pyqtSignal

from macrokit import Expr, Symbol, parse, Head
from magicgui.backends._qtpy.widgets import QBaseStringWidget
from magicgui.widgets.bases import ValueWidget
from magicclass.widgets._const import FONT

InjectorType = Union[Callable[[], "dict[str, Any]"], "dict[str, Any]"]
TranslatorType = Callable[[str, "dict[str, Any]"], "tuple[str, dict[str, Any]]"]


class HistoryStack:
    def __init__(self):
        self._history: list[str] = []
        self._index = -1

    def append(self, val: str):
        self._history.append(val)

    def pop(self):
        self._history.pop()

    def up(self) -> str | None:
        if self._index < 0:
            self._index = len(self._history) - 1
            if self._index < 0:
                return None
        else:
            self._index = max(self._index - 1, 0)
        return self._history[self._index]

    def down(self) -> str | None:
        if self._index >= len(self._history) - 1:
            self._index = -1
            return None
        else:
            self._index += 1
            return self._history[self._index]


class QRunnerLine(QtW.QTextEdit):
    executed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QtW.QTextEdit.LineWrapMode.NoWrap)
        self.setFixedHeight(24)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFont(QtGui.QFont(FONT))
        self._injector = default_injector
        self._translator = default_translator
        self._hist = HistoryStack()

    def setInjector(self, obj: InjectorType):
        if callable(obj):
            self._injector = obj
        else:
            self._injector = lambda: obj

    def setTranslator(self, obj: TranslatorType):
        if not callable(obj):
            raise TypeError("Translator must be callable.")
        self._translator = obj

    def execute(self):
        text = self.toPlainText()
        ns = self._injector()
        ns.setdefault("__builtins__", _DEFAULT_BUILTINS)
        text, ns = self._translator(text, ns)
        expr = parse(text)
        return self._execute(expr, ns)

    def _execute(self, expr: Expr, ns: dict[str, Any]):
        out = expr.eval(ns)
        self._hist.append(self.toPlainText())
        self.setPlainText("")
        return out

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Return:
            self.execute()
            return
        elif e.key() == Qt.Key.Key_Up:
            val = self._hist.up()
            if val is not None:
                self.setPlainText(val)
            return
        elif e.key() == Qt.Key.Key_Down:
            val = self._hist.down()
            if val is not None:
                self.setPlainText(val)
            else:
                self.setPlainText("")
            return
        elif e.key() == Qt.Key.Key_Escape:
            self.setPlainText("")
            return
        return super().keyPressEvent(e)


def reduce_getattr(symbols: list[Symbol | Expr]):
    if len(symbols) == 1:
        return symbols[0]
    return Expr(Head.getattr, [reduce_getattr(symbols[:-1]), symbols[-1]])


_DEFAULT_BUILTINS = {
    "int": int, "float": float, "str": str, "bool": bool, "list": list, "dict": dict, "tuple": tuple,
    "set": set, "frozenset": frozenset, "complex": complex, "bytes": bytes, "bytearray": bytearray,
    "print": print, "len": len, "range": range, "enumerate": enumerate, "zip": zip,
    "map": map, "filter": filter, "sum": sum, "min": min, "max": max, "abs": abs, "round": round,
    "all": all, "any": any, "sorted": sorted, "reversed": reversed, "type": type, "isinstance": isinstance,
}  # fmt: skip


def default_injector() -> dict[str, Any]:
    return {"__builtins__": _DEFAULT_BUILTINS}


def default_translator(text: str, ns: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    from magicclass import get_function_gui

    expr = parse(text)
    if isinstance(expr, Symbol):
        return text, ns
    if expr.head is Head.call:
        fexpr = expr.args[0]
        if isinstance(fexpr, Symbol):
            return text, ns
        if fexpr.head is Head.getattr:
            func_obj = fexpr.eval(ns)
            if not hasattr(func_obj, "__thread_worker__"):
                return text, ns
            symbols = fexpr.split_getattr()
            o = reduce_getattr(symbols[:-1])
            btn = Expr(Head.getitem, [o, str(symbols[-1])])
            get_function_gui(fexpr.eval(ns))
            fgui = Expr(Head.getattr, [btn, "mgui"])
            final_expr = Expr(Head.call, [fgui] + expr.args[1:])
            return str(final_expr), ns
    return text, ns


class QOneLineRunner(QtW.QWidget):
    def __init__(
        self,
        parent: QtW.QWidget | None = ...,
    ) -> None:
        super().__init__(parent)
        label = QtW.QLabel(">>", self)
        self._line = QRunnerLine(self)
        _layout = QtW.QHBoxLayout(self)
        _layout.addWidget(label)
        _layout.addWidget(self._line)
        self.setLayout(_layout)
        self.textChanged = self._line.textChanged

    def setInjector(self, obj: InjectorType):
        self._line.setInjector(obj)

    def setTranslator(self, obj: TranslatorType):
        self._line.setTranslator(obj)

    def execute(self):
        return self._line.execute()

    def text(self) -> str:
        return self._line.toPlainText()

    def setText(self, text: str):
        self._line.setPlainText(text)


class _OneLineRunner(QBaseStringWidget):
    _qwidget: QOneLineRunner

    def __init__(self, **kwargs):
        super().__init__(QOneLineRunner, "text", "setText", "textChanged", **kwargs)


class OneLineRunner(ValueWidget):
    executed = Signal(object)

    def __init__(self, injector=None, **kwargs):
        kwargs["widget_type"] = _OneLineRunner
        super().__init__(**kwargs)
        self.native: QOneLineRunner
        if injector is not None:
            self.native.setInjector(injector)
        self.native._line.executed.connect(self.executed)

    def execute(self):
        """Execute current text."""
        return self.native.execute()

    def set_injector(self, injector: InjectorType):
        """
        Set injector.

        Examples
        --------
        >>> runner = OneLineRunner()
        >>> runner.set_injector({"a": 1})
        >>> runner.value = "print(a)"
        >>> runner.execute()
        """
        self.native.setInjector(injector)

    def set_translator(self, translator: TranslatorType):
        """Set translator."""
        self.native.setTranslator(translator)
