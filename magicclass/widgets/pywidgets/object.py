from __future__ import annotations
from typing import Callable, Any
from functools import wraps
from collections import defaultdict
from qtpy.QtWidgets import QLabel, QMenu, QAction
from qtpy.QtCore import Qt
from ..utils import FreeWidget
from ...utils import Tooltips


_Callback = Callable[[Any, int], Any]


class BaseWidget(FreeWidget):
    # Abstract class for PyObject-like widgets.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title = QLabel(self.native)
        self._title.setAlignment(Qt.AlignCenter)
        self.running = False
        self.set_widget(self._title)
        self.title = self.name

        self._callbacks: defaultdict[type, list[_Callback]] = defaultdict(list)
        self._delegates: dict[type, Callable[[Any], str]] = dict()
        self._contextmenu: defaultdict[type, list[_Callback]] = defaultdict(list)
        self._tooltip: dict[type, Callable[[Any], str]] = dict()

    @property
    def value(self):
        raise NotImplementedError()

    @property
    def title(self) -> str:
        return self._title.text()

    @title.setter
    def title(self, text: str):
        self._title.setText(text)
        if text:
            self._title.show()
        else:
            self._title.hide()

    def register_callback(self, type_: type):
        """
        Register a double-click callback function for items of certain type.
        """

        def wrapper(func: Callable):
            self._callbacks[type_].append(func)
            return func

        return wrapper

    def register_delegate(self, type_: type):
        """
        Register a custom display.
        """

        def wrapper(func: Callable):
            self._delegates[type_] = func
            return func

        return wrapper

    def register_contextmenu(self, type_: type):
        """
        Register a custom context menu for items of certain type.
        """

        def wrapper(func: Callable):
            self._contextmenu[type_].append(func)
            return func

        return wrapper

    def register_tooltip(self, type_: type):
        """
        Register a custom tooltipfor items of certain type.
        """

        def wrapper(func: Callable | str):
            if isinstance(func, str):
                func = lambda x: func
            self._tooltip[type_] = func
            return func

        return wrapper


class ContextMenuMixin:
    """
    This class defines custom contextmenu with type dispatching.
    """

    def setContextMenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    def setParentWidget(self, widget: BaseWidget) -> None:
        self._parent = widget
        return None

    def contextMenu(self, point):
        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        item = self.itemAt(point)
        type_ = type(item.obj)
        menus = self._parent._contextmenu.get(type_, [])
        for f in menus:
            text = f.__name__.replace("_", " ")
            action = QAction(text, self)
            pfunc = partial_event(f, item.obj, self.row(item))
            action.triggered.connect(pfunc)
            doc = Tooltips(f).desc
            if doc:
                action.setToolTip(doc)
            menu.addAction(action)

        menu.exec_(self.mapToGlobal(point))


def partial_event(f, *args):
    @wraps(f)
    def _func(e):
        return f(*args)

    return _func


class PyObjectBound:
    def setObject(self, obj=None, name=None):
        if obj is not None:
            self.obj = obj
        if name is None:
            self.setText(str(obj))
        else:
            self.setText(name)
