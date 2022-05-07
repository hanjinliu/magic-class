from __future__ import annotations
from macrokit import Symbol, Expr, Head, Macro, parse
from typing import TYPE_CHECKING, Iterable, overload
from qtpy.QtWidgets import QMenuBar, QMenu, QAction
from magicgui.widgets import FileEdit

from ..widgets.misc import FreeWidget, ConsoleTextEdit
from ..utils import to_clipboard, show_messagebox

if TYPE_CHECKING:
    from ._base import BaseGui


# TODO: Tabs


class MacroEdit(FreeWidget):
    """A text edit embeded with a custom menu bar."""

    count = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__magicclass_parent__ = None
        self.textedit = ConsoleTextEdit()
        self.set_widget(self.textedit.native)
        self.native.setWindowTitle("Macro")

        self._synchronize = True
        self._set_menubar()

    @property
    def value(self):
        """Get macro text."""
        return self.textedit.value

    @value.setter
    def value(self, value: str):
        self.textedit.value = value

    @property
    def synchronize(self):
        """Update macro text in real time if true."""
        return self._synchronize

    @synchronize.setter
    def synchronize(self, value: bool):
        if value and not self._synchronize:
            parent = self._search_parent_magicclass()
            parent.macro._last_setval = None  # To avoid overwriting the last code.
        self._synchronize = value

    def load(self, path: str):
        """Load macro text from a file."""
        path = str(path)
        with open(path) as f:
            self.value = f.read()

    def save(self, path: str):
        """Save current macro text."""
        path = str(path)
        with open(path, mode="w") as f:
            f.write(self.value)

    def _close(self, e=None):
        """Close widget."""
        return self.close()

    def execute(self):
        """Execute macro."""
        parent = self._search_parent_magicclass()
        with parent.macro.blocked():
            try:
                # substitute :ui and :viewer to the actual objects
                code = parse(self.textedit.value)
                _ui = Symbol.var("ui")
                code.eval({_ui: parent})
            except Exception as e:
                show_messagebox(
                    "error", title=e.__class__.__name__, text=str(e), parent=self.native
                )

    def execute_lines(self, line_numbers: int | slice | Iterable[int] = -1):
        """Execute macro at selected lines."""
        parent = self._search_parent_magicclass()
        with parent.macro.blocked():
            try:
                code = parse(self.textedit.value)
                if isinstance(line_numbers, (int, slice)):
                    lines = code.args[line_numbers]
                else:
                    lines = "\n".join(code.args[l] for l in line_numbers)
                lines.eval({Symbol.var("ui"): parent})
            except Exception as e:
                show_messagebox(
                    "error", title=e.__class__.__name__, text=str(e), parent=self.native
                )

    def _create_duplicate(self, e=None):
        self.duplicate().show()

    def _get_complete(self, e=None):
        if self.value:
            self = self.duplicate()
            self.show()
        parent = self._search_parent_magicclass()
        self.value = str(parent.macro)

    def _auto_pep8(self, e=None):
        import autopep8

        self.value = autopep8.fix_code(self.value)
        parent = self._search_parent_magicclass()
        parent.macro._last_setval = None  # To avoid overwriting the last code.

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
        from ..utils import move_to_screen_center

        super().show()
        move_to_screen_center(self.native)

    def _execute(self, e=None):
        """Run macro."""
        self.execute()

    def _execute_selected(self, e=None):
        """Run selected line of macro."""
        parent = self._search_parent_magicclass()
        with parent.macro.blocked():
            try:
                all_code: str = self.textedit.value
                selected = self.textedit.selected
                code = parse(selected.strip())

                # to safely run code, every line should be fully selected even if selected
                # region does not raise SyntaxError.
                l = len(selected)
                start = all_code.find(selected)
                end = start + l
                if start != 0 and "\n" not in all_code[start - 1 : start + 1]:
                    raise SyntaxError("Select full line(s).")
                if end < l and "\n" not in all_code[end : end + 2]:
                    raise SyntaxError("Select full line(s).")

                code.eval({Symbol.var("ui"): parent})
            except Exception as e:
                show_messagebox(
                    "error", title=e.__class__.__name__, text=str(e), parent=self.native
                )

    def _search_parent_magicclass(self) -> BaseGui:
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

        run1_action = QAction("Execute selected lines", self._macro_menu)
        run1_action.triggered.connect(self._execute_selected)
        self._macro_menu.addAction(run1_action)

        create_action = QAction("Create", self._macro_menu)
        create_action.triggered.connect(self._create_duplicate)
        self._macro_menu.addAction(create_action)

        complete_action = QAction("Get complete macro", self._macro_menu)
        complete_action.triggered.connect(self._get_complete)
        self._macro_menu.addAction(complete_action)

        try:
            import autopep8

            pep8_action = QAction("Run PEP8", self._macro_menu)
            pep8_action.triggered.connect(self._auto_pep8)
            self._macro_menu.addAction(pep8_action)
        except ImportError:
            pass

        syn = QAction("Synchronize", self._macro_menu)
        syn.setCheckable(True)
        syn.setChecked(True)

        @syn.triggered.connect
        def _set_synchronize(check: bool):
            self.synchronize = check

        self._macro_menu.addAction(syn)
        self._synchronize_action = syn


class GuiMacro(Macro):
    def __init__(self, max_lines: int, flags={}):
        super().__init__(flags=flags)
        self._widget = None
        self._max_lines = max_lines
        self.callbacks.append(self._update_widget)

    @property
    def widget(self) -> MacroEdit:
        """Returns the macro editor."""
        if self._widget is None:
            self._widget = MacroEdit(name="Macro")
            from datetime import datetime

            now = datetime.now()
            self.append(Expr(Head.comment, [now.strftime("%Y/%m/%d %H:%M:%S")]))
        return self._widget

    def copy(self) -> Macro:
        """GuiMacro does not support deepcopy (and apparently _widget should not be copied)."""
        from copy import deepcopy

        return Macro(deepcopy(self.args), flags=self._flags)

    @overload
    def __getitem__(self, key: int) -> Expr:
        ...

    @overload
    def __getitem__(self, key: slice) -> Macro:
        ...

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Macro(self._args, flags=self.flags)
        return super().__getitem__(key)

    def _update_widget(self, expr=None):
        if self.widget.synchronize:
            self.widget.textedit.append(str(self.args[-1]))
        if len(self) > self._max_lines:
            del self[0]

    def _erase_last(self):
        if self.widget.synchronize:
            self.widget.textedit.erase_last()
