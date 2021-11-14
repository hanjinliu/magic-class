from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from qtpy.QtGui import QFont, QTextOption, QGuiApplication
from qtpy.QtWidgets import QMenuBar, QMenu, QAction, QMessageBox
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from magicgui.widgets import PushButton, TextEdit, FileEdit

from .utils import FrozenContainer

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

class Figure(FrozenContainer):
    """
    A matplotlib figure canvas.
    """    
    def __init__(self, 
                 nrows: int = 1,
                 ncols: int = 1,
                 figsize: tuple[int, int] = (4, 3),
                 style = None,
                 layout: str = "vertical", 
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
        
        super().__init__(layout=layout, labels=False, **kwargs)
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
        self.native.setFont(QFont("Consolas"))
        self.native.setWordWrapMode(QTextOption.NoWrap)
        
class MacroEdit(FrozenContainer):
    """
    A text edit embeded with a custom menu bar.
    """    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textedit = ConsoleTextEdit()
        self.set_widget(self.textedit.native)
        self.native: QWidget
        
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
        
    
    @property
    def value(self):
        return self.textedit.value
    
    @value.setter
    def value(self, value: str):
        self.textedit.value = value
    
    def _copy(self, e=None):
        """Copy text to clipboard"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.value)
    
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

class MessageBoxMode(Enum):
    ERROR = "error"
    WARNING = "warn"
    INFO = "info"
    QUESTION = "question"
    ABOUT = "about"

QMESSAGE_MODES = {
    MessageBoxMode.ERROR: QMessageBox.critical,
    MessageBoxMode.WARNING: QMessageBox.warning,
    MessageBoxMode.INFO: QMessageBox.information,
    MessageBoxMode.QUESTION: QMessageBox.question,
    MessageBoxMode.ABOUT: QMessageBox.about,
}

def show_messagebox(mode: str | MessageBoxMode = MessageBoxMode.INFO,
                    title: str = None,
                    text: str = None,
                    parent=None
                    ) -> bool:
    show_dialog = QMESSAGE_MODES[MessageBoxMode(mode)]
    result = show_dialog(parent, title, text)
    return result in (QMessageBox.Ok, QMessageBox.Yes)
