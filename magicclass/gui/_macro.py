from __future__ import annotations
from macrokit import Symbol, Expr, Head, Macro, parse
from typing import TYPE_CHECKING
from qtpy.QtWidgets import QMenuBar, QMenu, QAction
from magicgui.widgets import FileEdit

from ..widgets.misc import FreeWidget, ConsoleTextEdit
from ..utils import to_clipboard, show_messagebox

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget
    from ._base import BaseGui

# TODO: Tabs

class MacroEdit(FreeWidget):
    """
    A text edit embeded with a custom menu bar.
    """    
    count: int = 0
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__magicclass_parent__ = None
        self.textedit = ConsoleTextEdit()
        self.set_widget(self.textedit.native)
        self.native: QWidget
        self.native.setWindowTitle("Macro")
        
        self._synchronize = True
        self._set_menubar()
    
    @property
    def value(self):
        return self.textedit.value
    
    @value.setter
    def value(self, value: str):
        self.textedit.value = value
    
    @property
    def synchronize(self):
        return self._synchronize
    
    @synchronize.setter
    def synchronize(self, value: bool):
        if value and not self._synchronize:
            parent = self._search_parent_magicclass()
            parent.macro._last_setval = None # To avoid overwriting the last code.
        self._synchronize = value
        
    
    def load(self, path: str):
        path = str(path)
        with open(path, mode="r") as f:
            self.value = f.read()
        
    def save(self, path: str):
        path = str(path)
        with open(path, mode="w") as f:
            f.write(self.value)
    
    def _close(self, e=None):
        """Close widget."""
        return self.close()
    
    def execute(self):
        """
        Execute macro.
        """        
        parent = self._search_parent_magicclass()
        with parent.macro.blocked():
            try:
                code = parse(self.textedit.value)
                code.eval({Symbol.var("ui"): parent})
            except Exception as e:
                show_messagebox("error", title=e.__class__.__name__,
                                text=str(e), parent=self.native)
    
    def _open_in_new_window(self, e=None):
        self.duplicate().show()
    
    def new(self, name: str = None) -> MacroEdit:
        """
        Create a new widget with same parent magic class widget.

        Parameters
        ----------
        name : str, optional
            Widget name. This name will be the title.

        Returns
        -------
        MacroEdit
            New MacroEdit widget.
        """        
        if name is None:
            name = f"Macro-{self.__class__.count}"
            self.__class__.count += 1
        m = self.__class__(name=name)
        m.__magicclass_parent__ = self.__magicclass_parent__
        m.native.setParent(self.native.parent(), m.native.windowFlags())
        # Cannot synchronize sub widgets.
        m._synchronize = False
        m._synchronize_action.setChecked(False)
        m._synchronize_action.setEnabled(False)
        return m
    
    def duplicate(self, name=None) -> MacroEdit:
        """
        Create a new widget with same parent magic class widget. The code will be 
        duplicated to the new one.

        Parameters
        ----------
        name : str, optional
            Widget name. This name will be the title.

        Returns
        -------
        MacroEdit
            New MacroEdit widget.
        """     
        new = self.new(name=name)
        new.value = self.value
        return new
        
    def show(self):
        from ..utils import screen_center
        super().show()
        self.native.move(screen_center() - self.native.rect().center())
    
    def _execute(self, e=None):
        """Run macro"""
        self.execute()
            
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
            self.load(result)
        
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
            self.save(result)
    
    def _set_menubar(self):
        
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
        
        run_action = QAction("Execute", self._macro_menu)
        run_action.triggered.connect(self._execute)
        self._macro_menu.addAction(run_action)
        
        generate_action = QAction("Create", self._macro_menu)
        generate_action.triggered.connect(self._open_in_new_window)
        self._macro_menu.addAction(generate_action)
        
        syn = QAction("Synchronize", self._macro_menu)
        syn.setCheckable(True)
        syn.setChecked(True)
        @syn.triggered.connect
        def _set_synchronize(check: bool):
            self.synchronize = check
        self._macro_menu.addAction(syn)
        self._synchronize_action = syn
    

class GuiMacro(Macro):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widget = None
        self.callbacks.append(self._update_widget)
    
    @property
    def widget(self) -> MacroEdit:
        """
        Returns the macro editor.
        """
        if self._widget is None:
            self._widget = MacroEdit(name="Macro")
            from datetime import datetime
            now = datetime.now()
            self.append(Expr(Head.comment, [now.strftime("%Y/%m/%d %H:%M:%S")]))
        return self._widget
        
    def _update_widget(self, expr=None):
        if self.widget.synchronize:
            self.widget.textedit.append(str(self.args[-1]))
    
    def _erase_last(self):
        if self.widget.synchronize:
            self.widget.textedit.erase_last()