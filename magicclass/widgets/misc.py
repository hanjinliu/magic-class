from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy.QtGui import QTextCursor
from magicgui.widgets import PushButton, TextEdit

from .utils import FreeWidget

if TYPE_CHECKING:
    from qtpy.QtWidgets import QTextEdit

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