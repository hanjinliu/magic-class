from __future__ import annotations
from pathlib import Path

from typing import TYPE_CHECKING, Any, Iterable, overload
from qtpy import QtWidgets as QtW, QtCore
from macrokit import Symbol, Expr, Head, Macro, parse
from magicgui.widgets import FileEdit

from magicclass.widgets import CodeEdit, TabbedContainer, CommandRunner
from magicclass.utils import show_messagebox, move_to_screen_center

if TYPE_CHECKING:
    from ._base import BaseGui
    from .mgui_ext import Clickable


class MacroEdit(TabbedContainer):
    """A text edit embeded with a custom menu bar."""

    window_count = 0

    def __init__(self, **kwargs):
        super().__init__(labels=False, **kwargs)
        self.native: QtW.QWidget
        self.__magicclass_parent__ = None
        self.native.setWindowTitle("Macro")
        self.native_tab_widget.setTabBarAutoHide(True)
        self._native_macro = None
        self._recorded_macro = None
        self._command_runner = None
        self._set_menubar()

    def add_code_edit(self, name: str = "macro", native: bool = False) -> CodeEdit:
        """Add a new code edit widget as a new tab."""
        from magicclass import defaults

        textedit = CodeEdit(name=name)
        if native:
            if self._native_macro is not None:
                raise ValueError("Native macro already exists.")
            textedit.read_only = True
            self._native_macro = textedit

        self.append(textedit)
        if defaults["macro-highlight"]:
            textedit.syntax_highlight()
        return textedit

    def add_command_runner(self):
        self._command_runner = CommandRunner(name="Commands")
        self._command_runner.__magicclass_parent__ = self.__magicclass_parent__
        self.append(self._command_runner)
        return self._command_runner

    def get_selected_expr(self) -> Expr:
        """Return the selected code in the current code editor."""
        all_code: str = self.textedit.value
        selected = self.textedit.selected
        code = parse(selected.strip())

        # to safely run code, every line should be fully selected even if the
        # selected region does not raise SyntaxError.
        l = len(selected)
        start = all_code.find(selected)
        end = start + l
        if start != 0 and "\n" not in all_code[start - 1 : start + 1]:
            raise SyntaxError("Select full line(s).")
        if end < l and "\n" not in all_code[end : end + 2]:
            raise SyntaxError("Select full line(s).")
        return code

    def _create_command(self):
        parent = self._search_parent_magicclass()
        code = self.get_selected_expr()
        fn = lambda: code.eval({Symbol.var("ui"): parent})
        if self.command_runner is None:
            self.add_command_runner()
        tooltip = f"<b><code>{code}</code></b>"
        # replace \n with <br> to show multiline code in tooltip
        tooltip = tooltip.replace("\n", "<br>")
        self.command_runner.add_action(fn, tooltip=tooltip)

    @property
    def textedit(self) -> CodeEdit | None:
        """Return the current code editor"""
        wdt = self[self.current_index]
        if isinstance(wdt, CodeEdit):
            return wdt
        raise ValueError("This tab is not a code editor.")

    @property
    def native_macro(self) -> CodeEdit | None:
        """The code edit widget for the native macro"""
        return self._native_macro

    @property
    def recorded_macro(self) -> CodeEdit | None:
        """The code edit widget for the recording macro"""
        return self._recorded_macro

    @property
    def command_runner(self) -> CommandRunner | None:
        return self._command_runner

    def load(self, path: str):
        """Load macro text from a file."""
        _path = Path(path)
        with open(_path) as f:
            edit = self.new_tab(_path.stem)
            edit.value = f.read()

    def save(self, path: str):
        """Save current macro text."""
        path = str(path)
        with open(path, mode="w") as f:
            f.write(self.textedit.value)

    def _close(self, e=None):
        """Close widget."""
        return self.close()

    def execute(self):
        """Execute macro."""
        self._execute(parse(self.textedit.value))

    def _create_native_duplicate(self, e=None):
        new = self.new_tab("script")
        new.value = self.native_macro.value
        return new

    def new_tab(self, name: str | None = None) -> CodeEdit:
        if name is None:
            name = "script"
        # find unique name
        suffix = 0
        tab_name = name
        existing_names = {tab.name for tab in self}
        while tab_name in existing_names:
            tab_name = f"{name}-{suffix}"
            suffix += 1
        new = self.add_code_edit(tab_name)
        self.current_index = len(self) - 1
        return new

    def new_window(self, name: str = None) -> MacroEdit:
        """
        Create a new window with same parent magic class widget.

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
            name = f"Macro-{self.__class__.window_count}"
            self.__class__.window_count += 1
        new = self.__class__(name=name)
        new.__magicclass_parent__ = self.__magicclass_parent__
        new.native.setParent(self.native.parent(), new.native.windowFlags())
        new.show()
        geometry = self.native.geometry()
        geometry.moveTopLeft(geometry.topLeft() + QtCore.QPoint(20, 20))
        new.native.setGeometry(geometry)
        return new

    def duplicate_tab(self):
        new = self.new_tab(self.textedit.name)
        new.value = self.textedit.value
        self.current_index = len(self) - 1
        return new

    def delete_tab(self):
        index = self.current_index
        del self[index]

    def show(self):
        super().show()
        move_to_screen_center(self.native)

    def _execute(self, code: Expr):
        """Run macro."""
        parent = self._search_parent_magicclass()
        try:
            if str(code) == "":
                raise ValueError("No code selected")
            ns = {Symbol.var("ui"): parent}
            if (viewer := parent.parent_viewer) is not None:
                ns.setdefault(Symbol.var("viewer"), viewer)
            code.eval()
        except Exception as e:
            show_messagebox(
                "error", title=e.__class__.__name__, text=str(e), parent=self.native
            )

    def _execute_selected(self, e=None):
        """Run selected line of macro."""
        self._execute(self.get_selected_expr())

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

    def _start_recording(self):
        self._recorded_macro = self.textedit

    def _finish_recording(self):
        self._recorded_macro = None

    def _set_menubar(self):

        self._menubar = QtW.QMenuBar(self.native)
        self.native.layout().setMenuBar(self._menubar)

        # set file menu
        self._file_menu = QtW.QMenu("File", self.native)
        self._menubar.addMenu(self._file_menu)

        self._file_menu.addAction("New window", self.new_window, "Ctrl+Shift+N")
        self._file_menu.addSeparator()
        self._file_menu.addAction("Open file", self._load, "Ctrl+O")
        self._file_menu.addAction("Save", self._save, "Ctrl+S")
        self._file_menu.addSeparator()
        self._file_menu.addAction("Close", self._close)

        self._tab_menu = QtW.QMenu("Tab", self.native)
        self._menubar.addMenu(self._tab_menu)
        self._tab_menu.addAction("New tab", self.new_tab, "Ctrl+T")
        self._tab_menu.addAction("Duplicate tab", self.duplicate_tab, "Ctrl+D")
        self._tab_menu.addAction(
            "Current macro in new tab", self._create_native_duplicate
        )
        self._tab_menu.addAction("Delete tab", self.delete_tab, "Ctrl+W")

        # set macro menu
        self._macro_menu = QtW.QMenu("Macro", self.native)
        self._menubar.addMenu(self._macro_menu)

        self._macro_menu.addAction("Execute", self.execute, "Ctrl+F5")
        self._macro_menu.addAction(
            "Execute selected lines", self._execute_selected, "Ctrl+Shift+F5"
        )
        self._macro_menu.addSeparator()
        _action_start = self._macro_menu.addAction(
            "Start recording",
            self._start_recording,
        )
        _action_finish = self._macro_menu.addAction(
            "Finish recording", self._finish_recording
        )
        self._macro_menu.addAction("Create command", self._create_command)

        _action_finish.setEnabled(False)
        _action_start.triggered.connect(lambda: _action_finish.setEnabled(True))
        _action_finish.triggered.connect(lambda: _action_finish.setEnabled(False))


class GuiMacro(Macro):
    """Macro object with GUI-specific functions."""

    def __init__(self, max_lines: int, flags={}):
        super().__init__(flags=flags)
        self._widget = None
        self._max_lines = max_lines
        self.callbacks.append(self._update_widget)

    @property
    def widget(self) -> MacroEdit:
        """Returns the macro editor."""
        from datetime import datetime

        if self._widget is None:
            self._widget = MacroEdit(name="Macro")
            self._widget.add_code_edit(native=True)
            now = datetime.now()
            self.append(Expr(Head.comment, [now.strftime("%Y/%m/%d %H:%M:%S")]))
        return self._widget

    @property
    def _gui_parent(self) -> BaseGui:
        """The parent GUI object."""
        return self.widget.__magicclass_parent__

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
            return Macro(self._args, flags=self.flags)[key]
        return super().__getitem__(key)

    def subset(self, indices: Iterable[int]) -> Macro:
        """Generate a subset of macro."""
        args = [self._args[i] for i in indices]
        return Macro(args, flags=self.flags)

    def get_evaluator(self, key: int | slice | Iterable[int], ns: dict[str, Any] = {}):
        if isinstance(key, (int, slice)):
            subset = self[key]
        else:
            subset = self.subset(key)
        ns = dict(ns)
        ui = self._gui_parent
        ns.setdefault("ui", ui)
        if (viewer := ui.parent_viewer) is not None:
            ns.setdefault("viewer", viewer)
        return lambda: subset.eval(ns)

    def repeat_method(
        self, index: int = -1, same_args: bool = False, wait: bool = False
    ) -> None:
        _object, _args, _kwargs = self[index].split_call()
        _ui, *_attributes, _last = _object.split_getattr()
        ui = self._gui_parent
        assert _ui == ui._my_symbol
        ins = ui
        for attr in _attributes:
            ins = getattr(ins, attr.name)

        wdt: Clickable = ins[_last.name]
        if not wait:
            if same_args:
                wdt.mgui.call_button.changed()
            else:
                wdt.changed()
        else:
            if same_args:
                wdt.mgui()
            else:
                raise NotImplementedError(
                    "wait=True and same_args=False is not implemented yet."
                )
        return None

    def _update_widget(self, expr=None):
        line = str(self.args[-1])
        if wdt := self.widget.native_macro:
            wdt.append(line)
        if wdt := self.widget.recorded_macro:
            wdt.append(line)
        if len(self) > self._max_lines:
            del self[0]

    def _erase_last(self):
        if wdt := self.widget.native_macro:
            wdt.erase_last()
        if wdt := self.widget.recorded_macro:
            wdt.erase_last()
