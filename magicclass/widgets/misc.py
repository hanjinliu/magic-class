from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QMenuBar, QMenu, QAction
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from magicgui.widgets import PushButton, TextEdit, FileEdit

from .utils import FreeWidget
from ..utils import to_clipboard

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

class Figure(FreeWidget):
    """
    A matplotlib figure canvas.
    """    
    def __init__(self, 
                 nrows: int = 1,
                 ncols: int = 1,
                 figsize: tuple[int, int] = (4, 3),
                 style = None, 
                 **kwargs):
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
        
    def draw(self):
        self.figure.tight_layout()
        self.figure.canvas.draw()
    
    @property
    def axes(self):
        return self.figure.axes
    
    @property
    def ax(self):
        try:
            _ax = self.axes[0]
        except IndexError:
            _ax = self.figure.add_subplot(111)
        return _ax
        

class ConsoleTextEdit(TextEdit):
    """
    A text edit with console-like setting.
    """    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from qtpy.QtGui import QFont, QTextOption
        self.native.setFont(QFont("Consolas"))
        self.native.setWordWrapMode(QTextOption.NoWrap)
        
class MacroEdit(FreeWidget):
    """
    A text edit embeded with a custom menu bar.
    """    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textedit = ConsoleTextEdit()
        self.set_widget(self.textedit.native)
        self.native: QWidget
        self.native.setWindowTitle("Macro")
        
        self._menubar = QMenuBar(self.native)
        self.native.layout().setMenuBar(self._menubar)
        
        self.textedit.read_only = False
        vbar = self.textedit.native.verticalScrollBar()
        vbar.setValue(vbar.maximum())
        
        # set menu
        self._file_menu = QMenu("File", self.native)
        self._menubar.addMenu(self._file_menu)
        
        # Set actions to menus
        copy_action = QAction("Copy", self._file_menu)
        copy_action.triggered.connect(self._copy)
        self._file_menu.addAction(copy_action)
        
        save_action = QAction("Save", self._file_menu)
        save_action.triggered.connect(self._save)
        self._file_menu.addAction(save_action)
        
        close_action = QAction("Close", self._file_menu)
        close_action.triggered.connect(self._close)
        self._file_menu.addAction(close_action)
    
    def addText(self, text: str):
        self.textedit.native.append(text)
    
    def erase_last_line(self):
        cursor = self.textedit.native.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.textedit.native.setTextCursor(cursor)
    
    @property
    def value(self):
        return self.textedit.value
    
    @value.setter
    def value(self, value: str):
        self.textedit.value = value
    
    def _copy(self, e=None):
        """Copy text to clipboard"""
        to_clipboard(self.value)
    
    def _save(self, e=None):
        """Save text."""
        fdialog = FileEdit(mode="w", filter="*.txt;*.py")
        result = fdialog._show_file_dialog(
                    fdialog.mode,
                    caption=fdialog._btn_text,
                    start_path=str(fdialog.value),
                    filter=fdialog.filter,
                    )
        if result:
            path = str(result)
            with open(path, mode="w") as f:
                f.write(self.value)
    
    def _close(self, e=None):
        """Close widget."""
        self.native.close()
        self.native.deleteLater()
        

class CheckButton(PushButton):
    """
    A checkable button.
    """    
    def __init__(self, text: str | None = None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native.setCheckable(True)