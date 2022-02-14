from __future__ import annotations
from typing import TYPE_CHECKING, Iterable, MutableSequence, Any
from qtpy.QtWidgets import QTabWidget, QLineEdit, QMenu
from qtpy.QtGui import QTextCursor
from qtpy.QtCore import Qt
from magicgui.widgets import PushButton, TextEdit, Table, Container, CheckBox
from magicgui.widgets._bases.value_widget import ValueWidget, UNSET
from .utils import FreeWidget

if TYPE_CHECKING:
    from qtpy.QtWidgets import QTextEdit
    from matplotlib.axes import Axes


class OptionalWidget(Container):
    """A container that can represent optional argument."""
    def __init__(self, widget: ValueWidget, text: str = None, layout="vertical", 
                 nullable=True, value=None, options=None, **kwargs):
        if text is None:
            text = f"set {kwargs.get('name', 'value')}"
        self._checkbox = CheckBox(text=text, value=True)
        self._inner_value_widget = widget
        super().__init__(layout=layout, widgets=(self._checkbox, self._inner_value_widget), 
                         labels=True, **kwargs)
        @self._checkbox.changed.connect
        def _toggle_visibility(v: bool):
            self._inner_value_widget.visible = v
        self.value = value
    
    @property
    def value(self) -> Any:
        if self._checkbox.value:
            return self._inner_value_widget.value
        else:
            return None
    
    @value.setter
    def value(self, v: Any) -> None:
        if v is None or v is UNSET:
            self._checkbox.value = False
        else:
            self._inner_value_widget.value = v
            self._checkbox.value = True
    
    @property
    def text(self) -> str:
        return self._checkbox.text
    
    @text.setter
    def text(self, v: str) -> None:
        self._checkbox.text = v 
        

class Figure(FreeWidget):
    """A matplotlib figure canvas."""
    def __init__(self, 
                 nrows: int = 1,
                 ncols: int = 1,
                 figsize: tuple[int, int] = (4, 3),
                 style = None, 
                 **kwargs):
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvas
        
        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            if style is None:
                fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
            else:
                with plt.style.context(style):
                    fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
        finally:
            mpl.use(backend)
        
        super().__init__(**kwargs)
        canvas = FigureCanvas(fig)
        self.set_widget(canvas)
        self.figure = fig
        self.min_height = 40
        
        for name, method in self.__class__.__dict__.items():
            if name.startswith("_") or getattr(method, "__doc__", None) is None:
                continue
            plt_method = getattr(plt, name, None)
            plt_doc = getattr(plt_method, "__doc__", "")
            if plt_doc:
                method.__doc__ += f"\nOriginal docstring:\n\n{plt_doc}"
        
    def draw(self):
        """Copy of ``plt.draw()``."""
        self.figure.tight_layout()
        self.figure.canvas.draw()
        
    def clf(self):
        """Copy of ``plt.clf``."""
        self.figure.clf()
        self.draw()
    
    def cla(self):
        """Copy of ``plt.cla``."""
        self.ax.cla()
        self.draw()
    
    @property
    def axes(self) -> "list[Axes]":
        return self.figure.axes
    
    @property
    def ax(self) -> "Axes":
        try:
            _ax = self.axes[0]
        except IndexError:
            _ax = self.figure.add_subplot(111)
        return _ax
    
    def plot(self, *args, **kwargs) -> "Axes":
        """Copy of ``plt.plot``."""
        self.ax.plot(*args, **kwargs)
        self.draw()
        return self.ax
    
    def scatter(self, *args, **kwargs) -> "Axes":
        """Copy of ``plt.scatter``."""
        self.ax.scatter(*args, **kwargs)
        self.draw()
        return self.ax
    
    def hist(self, *args, **kwargs):
        """Copy of ``plt.hist``."""
        self.ax.hist(*args, **kwargs)
        self.draw()
        return self.ax
    
    def text(self, *args, **kwargs):
        """Copy of ``plt.text``."""
        self.ax.text(*args, **kwargs)
        self.draw()
        return self.ax
        
    def xlim(self, *args, **kwargs):
        """Copy of ``plt.xlim``."""
        ax = self.ax
        if not args and not kwargs:
            return ax.get_xlim()
        ret = ax.set_xlim(*args, **kwargs)
        self.draw()
        return ret

    def ylim(self, *args, **kwargs):
        """Copy of ``plt.ylim``."""
        ax = self.ax
        if not args and not kwargs:
            return ax.get_ylim()
        ret = ax.set_ylim(*args, **kwargs)
        self.draw()
        return ret
    
    def imshow(self, *args, **kwargs) -> "Axes":
        """Copy of ``plt.imshow``."""
        self.ax.imshow(*args, **kwargs)
        self.draw()
        return self.ax
    
    def legend(self, *args, **kwargs):
        """Copy of ``plt.legend``."""
        leg = self.ax.legend(*args, **kwargs)
        self.draw()
        return leg
    
    def title(self, *args, **kwargs):
        """Copy of ``plt.title``."""
        title = self.ax.set_title(*args, **kwargs)
        self.draw()
        return title
    
    def xlabel(self, *args, **kwargs):
        """Copy of ``plt.xlabel``."""
        xlabel = self.ax.set_xlabel(*args, **kwargs)
        self.draw()
        return xlabel
    
    def ylabel(self, *args, **kwargs):
        """Copy of ``plt.ylabel``."""
        ylabel = self.ax.set_ylabel(*args, **kwargs)
        self.draw()
        return ylabel


class ConsoleTextEdit(TextEdit):
    """A text edit with console-like setting."""    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from qtpy.QtGui import QFont, QTextOption
        self.native: QTextEdit
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        self.native.setFont(font)
        self.native.setWordWrapMode(QTextOption.NoWrap)
        
        # set tab width
        self.tab_size = 4
    
    @property
    def tab_size(self):
        metrics = self.native.fontMetrics()
        return self.native.tabStopWidth() // metrics.width(" ")
    
    @tab_size.setter
    def tab_size(self, size: int):
        metrics = self.native.fontMetrics()
        self.native.setTabStopWidth(size*metrics.width(" "))
        
    def append(self, text: str):
        """Append new text."""
        self.native.append(text)
    
    def erase_last(self):
        """Erase the last line."""
        cursor = self.native.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.native.setTextCursor(cursor)
    
    @property
    def selected(self) -> str:
        """Return selected string."""
        cursor = self.native.textCursor()
        return cursor.selectedText().replace(u"\u2029", "\n")

class CheckButton(PushButton):
    """A checkable button."""
    def __init__(self, text: str | None = None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native.setCheckable(True)

class _QtSpreadSheet(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setMovable(True)
        self._n_table = 0
        self.tabBar().tabBarDoubleClicked.connect(self.editTabBarLabel)
        self.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self.showContextMenu)
        self._line_edit = None
    
    def addTable(self, table):
        self.addTab(table, f"Sheet {self._n_table}")
        self._n_table += 1
    
    def renameTab(self, index: int, name: str) -> None:
        self.tabBar().setTabText(index, name)
        return None
    
    def editTabBarLabel(self, index: int):
        if index < 0:
            return
        if self._line_edit is not None:
            self._line_edit.deleteLater()
            self._line_edit = None
            
        tabbar = self.tabBar()
        self._line_edit = QLineEdit(self)
        @self._line_edit.editingFinished.connect        
        def _(_=None):
            self.renameTab(index, self._line_edit.text())
            self._line_edit.deleteLater()
            self._line_edit = None
        self._line_edit.setText(tabbar.tabText(index))  
        self._line_edit.setGeometry(tabbar.tabRect(index))
        self._line_edit.setFocus()
        self._line_edit.selectAll()
        self._line_edit.show()
    
    def showContextMenu(self, point):
        if point.isNull():
            return
        tabbar = self.tabBar()
        index = tabbar.tabAt(point)
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda _: self.editTabBarLabel(index))
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda _: self.removeTab(index))
        
        menu.exec(tabbar.mapToGlobal(point))


class SpreadSheet(FreeWidget, MutableSequence[Table]):
    """A simple spread sheet widget."""
    
    def __init__(self):
        super().__init__()
        spreadsheet = _QtSpreadSheet()
        self.set_widget(spreadsheet)
        self.central_widget: _QtSpreadSheet
        self._tables: list[Table] = []
    
    def __len__(self) -> int:
        return self.central_widget.count()
        
    def index(self, item: Table | str):
        if isinstance(item, Table):
            for i, table in enumerate(self._tables):
                if item is table:
                    return i
            else:
                raise ValueError
        elif isinstance(item, str):
            tabbar = self.central_widget.tabBar()
            for i in range(tabbar.count()):
                text = tabbar.tabText(i)
                if text == item:
                    return i
            else:
                raise ValueError
        else:
            raise TypeError

    
    def __getitem__(self, key):
        if isinstance(key, str):
            key = self.index(key)
        return self._tables[key]
    
    def __setitem__(self, key, value):
        raise NotImplementedError
    
    def __delitem__(self, key):
        if isinstance(key, str):
            key = self.index(key)
        self.central_widget.removeTab(key)
        del self._tables[key]
    
    def __iter__(self) -> Iterable[Table]:
        return iter(self._tables)
        
    def insert(self, key: int, value):
        if key < 0:
            key += len(self)
        table = Table(value=value)
        self.central_widget.addTable(table.native)
        self._tables.insert(key, table)
    
    def rename(self, index: int, name: str):
        self.central_widget.renameTab(index, name)
        return None
