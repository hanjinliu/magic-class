from __future__ import annotations
from macrokit import Symbol, Expr, Head, Macro
from typing import TYPE_CHECKING
from qtpy.QtWidgets import QMenuBar, QMenu, QAction
from magicgui.widgets import FileEdit

from ..widgets.misc import FreeWidget, ConsoleTextEdit
from ..utils import to_clipboard

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget
    from ._base import BaseGui
    
class MacroEdit(FreeWidget):
    """
    A text edit embeded with a custom menu bar.
    """    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__magicclass_parent__ = None
        self.textedit = ConsoleTextEdit()
        self.set_widget(self.textedit.native)
        self.native: QWidget
        self.native.setWindowTitle("Macro")
        
        self._menubar = QMenuBar(self.native)
        self.native.layout().setMenuBar(self._menubar)
        
        self.textedit.read_only = False
        vbar = self.textedit.native.verticalScrollBar()
        vbar.setValue(vbar.maximum())
        
        # set file menu
        self._file_menu = QMenu("File", self.native)
        self._menubar.addMenu(self._file_menu)
        
        load_action = QAction("Load", self._file_menu)
        load_action.triggered.connect(self._load)
        self._file_menu.addAction(load_action)
        
        copy_action = QAction("Copy", self._file_menu)
        copy_action.triggered.connect(self._copy)
        self._file_menu.addAction(copy_action)
        
        save_action = QAction("Save", self._file_menu)
        save_action.triggered.connect(self._save)
        self._file_menu.addAction(save_action)
        
        close_action = QAction("Close", self._file_menu)
        close_action.triggered.connect(self._close)
        self._file_menu.addAction(close_action)
        
        # set macro menu
        self._macro_menu = QMenu("Macro", self.native)
        self._menubar.addMenu(self._macro_menu)
        
        run_action = QAction("Run", self._macro_menu)
        run_action.triggered.connect(self._run)
        self._macro_menu.addAction(run_action)
        
        generate_action = QAction("Open in New Window", self._macro_menu)
        generate_action.triggered.connect(self._open_in_new_window)
        self._macro_menu.addAction(generate_action)
    
    @property
    def value(self):
        return self.textedit.value
    
    @value.setter
    def value(self, value: str):
        self.textedit.value = value
        
    def _search_parent_magicclass(self) -> "BaseGui":
        current_self = self
        while getattr(current_self, "__magicclass_parent__", None) is not None:
            current_self = current_self.__magicclass_parent__
        return current_self
    
    def _load(self, e=None):
        """Load macro"""
        fdialog = FileEdit(mode="r", filter="*.txt;*.py")
        result = fdialog._show_file_dialog(
                    fdialog.mode,
                    caption=fdialog._btn_text,
                    start_path=str(fdialog.value),
                    filter=fdialog.filter,
                    )
        if result:
            path = str(result)
            with open(path, mode="r") as f:
                self.value = f.read()
        
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
    
    def _run(self, e=None):
        """Run macro"""
        parent = self._search_parent_magicclass()
        with parent.macro.blocked():
            parent.macro.eval({Symbol.var("ui"): parent})
    
    def _open_in_new_window(self, e=None):
        m = self.__class__(name="Generated Macro")
        m.value = self.value
        m.__magicclass_parent__ = self.__magicclass_parent__
        m.show()
    
    def show(self):
        from ..utils import screen_center
        super().show()
        self.native.move(screen_center() - self.native.rect().center())
        


class GuiMacro(Macro):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widget = None
        self.callbacks.append(self._update_widget)
    
    @property
    def widget(self) -> MacroEdit:
        """
        Returns the text edit widget.
        """
        if self._widget is None:
            self._widget = MacroEdit(name="Macro")
            from datetime import datetime
            now = datetime.now()
            self.append(Expr(Head.comment, [now.strftime("%Y/%m/%d %H:%M:%S")]))
        return self._widget
    
    def _update_widget(self, e=None):
        self.widget.textedit.append(str(self.args[-1]))