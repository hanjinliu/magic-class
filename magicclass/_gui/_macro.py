from __future__ import annotations
from pathlib import Path

from typing import TYPE_CHECKING, Any, Callable, Iterable, overload
import warnings
from qtpy import QtWidgets as QtW, QtCore
from macrokit import Symbol, Expr, Head, Macro, parse
from magicgui.widgets import FileEdit, LineEdit

from magicclass.widgets import CodeEdit, TabbedContainer, ScrollableContainer, Dialog
from magicclass.utils import move_to_screen_center
from magicclass._gui.runner import CommandRunnerMenu

if TYPE_CHECKING:
    from ._base import BaseGui
    from .mgui_ext import Clickable


class MacroEdit(TabbedContainer):
    """A text edit embeded with a custom menu bar."""

    window_count = 0

    def __init__(self, **kwargs):
        super().__init__(labels=False, **kwargs)
        self.native: QtW.QWidget
        self.__magicclass_parent__: BaseGui | None = None
        self.native.setWindowTitle("Macro")
        self.native_tab_widget.setTabBarAutoHide(True)
        self._native_macro = None
        self._recorded_macro = None
        self._set_menubar()

    def _add_code_edit(self, name: str = "macro", native: bool = False) -> CodeEdit:
        """Add a new code edit widget as a new tab."""
        from magicclass._gui._base import defaults

        textedit = CodeEdit(name=name)
        if native:
            if self._native_macro is not None:
                raise ValueError("Native macro already exists.")
            textedit.read_only = True
            self._native_macro = textedit

        self.append(textedit)
        if defaults["macro-highlight"]:
            textedit.syntax_highlight()
        textedit.__magicclass_parent__ = self.__magicclass_parent__
        textedit.executing.connect(self._on_executing)
        return textedit

    def _on_executing(self, desc: str):
        if desc == "exec-line":
            self._execute_selected()
        elif desc == "register-command":
            self._create_command()
        else:
            raise RuntimeError(f"Unknown executing description: {desc}")

    def get_selected_expr(self) -> Expr:
        """Return the selected code in the current code editor."""
        all_code: str = self.textedit.value
        selected = self.textedit.selected

        # to safely run code, every line should be fully selected even if the
        # selected region does not raise SyntaxError.
        l = len(selected)
        start = all_code.find(selected)
        end = start + l
        if start != 0 and "\n" not in all_code[start - 1 : start + 1]:
            raise SyntaxError("Select full line(s).")
        if end < l and "\n" not in all_code[end : end + 2]:
            raise SyntaxError("Select full line(s).")

        code = parse(selected.strip())
        return code

    def _create_command(self):
        """Create command from the selected code."""
        parent = self._search_parent_magicclass()
        code = self.get_selected_expr()
        fn = lambda: code.eval({Symbol.var("ui"): parent})
        tooltip = f"<b><code>{code}</code></b>"
        # replace \n with <br> to show multiline code in tooltip
        tooltip = tooltip.replace("\n", "<br>")
        self._command_menu.add_action(fn, tooltip=tooltip)

    def _rename_command(self):
        """Rename currently registered commands."""
        cnt = ScrollableContainer()
        for i, action in enumerate(self._command_menu):
            cnt.append(
                LineEdit(label=str(i), value=action.text, tooltip=action.tooltip)
            )
        dlg = Dialog(widgets=[cnt], parent=self)
        dlg.exec()
        for i, line in enumerate(cnt):
            action = self._command_menu[i]
            action.text = line.value

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
        new = self._add_code_edit(tab_name)
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
        new._add_code_edit()
        new.show()
        geometry = self.native.geometry()
        geometry.moveTopLeft(geometry.topLeft() + QtCore.QPoint(20, 20))
        new.native.setGeometry(geometry)
        return new

    def duplicate(self, name: str = None):
        warnings.warn(
            "duplicate() is deprecated. MacroEdit is now a tabbed widget. "
            "Use 'new_window()' or 'new_tab()' instead.",
            DeprecationWarning,
        )
        current = self.textedit
        text = current.value
        new = self.new_window(name=name)
        new.textedit.value = text
        return new

    def new(self, name: str = None):
        warnings.warn(
            "new() is deprecated. MacroEdit is now a tabbed widget. "
            "Use 'new_window()' or 'new_tab()' instead.",
            DeprecationWarning,
        )
        return self.new_window(name=name)

    def _new_tab(self, e=None):
        self.new_tab()

    def _duplicate_tab(self, e=None):
        current_value = self.textedit.value
        new = self.new_tab(self.textedit.name)
        new.value = current_value
        self.current_index = len(self) - 1

    def _delete_tab(self, e=None):
        if len(self) == 0:
            return
        index = self.current_index
        if self[index] is not self.native_macro:
            """Don't delete the native macro tab."""
            del self[index]

    def _zoom_in(self, e=None):
        self.textedit.zoom_in()

    def _zoom_out(self, e=None):
        self.textedit.zoom_out()

    def show(self):
        if self.parent is None:
            ui = self.__magicclass_parent__
            self.native.setParent(ui.native, self.native.windowFlags())
        super().show()
        move_to_screen_center(self.native)
        self.textedit.native.setFocus()

    def _execute(self, code: Expr):
        """Run macro."""
        parent = self._search_parent_magicclass()
        try:
            if str(code) == "":
                raise ValueError("No code selected")
            ns = {Symbol.var("ui"): parent}
            if (viewer := parent.parent_viewer) is not None:
                ns.setdefault(Symbol.var("viewer"), viewer)
            code.eval(ns)
        except Exception as e:
            parent._error_mode.get_handler()(e, self)

    def _execute_selected(self, e=None):
        """Run selected line of macro."""
        self._execute(self.get_selected_expr())

    def execute_lines(self, indices: int | slice | Iterable[int]):
        all_text: str = self.textedit.value
        lines = all_text.split("\n")
        if isinstance(indices, int):
            input_text = lines[indices]
        elif isinstance(indices, slice):
            input_text = "\n".join(lines[indices])
        else:
            input_text = "\n".join(lines[i] for i in indices)
        code = parse(input_text)
        return self._execute(code)

    def _search_parent_magicclass(self) -> BaseGui:
        current_self = self
        while getattr(current_self, "__magicclass_parent__", None) is not None:
            current_self = current_self.__magicclass_parent__
        return current_self

    def _new_window(self, e=None):
        self.new_window()

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
        index = self.current_index
        if self[index] is self.native_macro:
            self.new_tab("record")
        self._recorded_macro = self.textedit

    def _finish_recording(self):
        self._recorded_macro = None

    def _set_menubar(self):
        self._menubar = QtW.QMenuBar(self.native)
        self.native.layout().setMenuBar(self._menubar)

        # fmt: off
        self._file_menu = QtW.QMenu("File", self.native)
        self._file_menu.setToolTipsVisible(True)
        self._menubar.addMenu(self._file_menu)

        self._file_menu.addAction("New window", self._new_window, "Ctrl+Shift+N").setToolTip("Open a new macro editor")
        self._file_menu.addSeparator()
        self._file_menu.addAction("Open file", self._load, "Ctrl+O").setToolTip("Open a python file")
        self._file_menu.addAction("Save", self._save, "Ctrl+S").setToolTip("Save the macro as a python file")
        self._file_menu.addSeparator()
        self._file_menu.addAction("Close", self._close).setToolTip("Close this macro editor")

        self._tab_menu = QtW.QMenu("Tab", self.native)
        self._tab_menu.setToolTipsVisible(True)
        self._menubar.addMenu(self._tab_menu)
        self._tab_menu.addAction("New tab", self._new_tab, "Ctrl+T").setToolTip("Open a new empty tab")
        self._tab_menu.addAction("Duplicate tab", self._duplicate_tab, "Ctrl+D").setToolTip("Duplicate current tab as a new tab")
        self._tab_menu.addAction("Current macro in new tab", self._create_native_duplicate).setToolTip("Duplicate current GUI macro in a new tab")
        self._tab_menu.addAction("Delete tab", self._delete_tab, "Ctrl+W").setToolTip("Delete current tab")
        self._tab_menu.addSeparator()
        self._tab_menu.addAction("Zoom in", self._zoom_in, "Ctrl+Shift+.").setToolTip("Zoom in the text")
        self._tab_menu.addAction("Zoom out", self._zoom_out, "Ctrl+Shift+,").setToolTip("Zoom out the text")


        # set macro menu
        self._macro_menu = QtW.QMenu("Macro", self.native)
        self._macro_menu.setToolTipsVisible(True)
        self._menubar.addMenu(self._macro_menu)

        self._macro_menu.addAction("Execute", self.execute, "Ctrl+F5").setToolTip("Execute the entire script of the current tab")
        self._macro_menu.addAction("Execute selected lines", self._execute_selected, "Ctrl+Shift+F5").setToolTip("Execute the selected lines of the current tab")
        self._macro_menu.addSeparator()
        _action_start = self._macro_menu.addAction("Start recording", self._start_recording)
        _action_finish = self._macro_menu.addAction("Finish recording", self._finish_recording)

        _action_finish.setEnabled(False)
        _action_start.triggered.connect(lambda: _action_finish.setEnabled(True))
        _action_start.setToolTip("Open a new tab and start recording GUI operations in it")
        _action_finish.triggered.connect(lambda: _action_finish.setEnabled(False))
        _action_finish.setToolTip("Finish recording task started by 'Start recording' menu")

        self._command_menu = CommandRunnerMenu(
            "Command",
            parent=self.native,
            magicclass_parent=self._search_parent_magicclass(),
        )
        self._command_menu.native.setToolTipsVisible(True)
        self._menubar.addMenu(self._command_menu.native)
        self._command_menu.native.addAction("Create command", self._create_command).setToolTip("Create a command using the selected lines")
        self._command_menu.native.addAction("Rename command", self._rename_command).setToolTip("Rename regeistered commands.")
        self._command_menu.native.addSeparator()
        # fmt: on


class GuiMacro(Macro):
    """Macro object with GUI-specific functions."""

    def __init__(self, max_lines: int, flags={}, ui: BaseGui = None):
        from datetime import datetime

        super().__init__(flags=flags)
        self._max_lines = max_lines
        self.callbacks.append(self._update_widget)

        self._widget = MacroEdit(name="Macro")
        self._widget.__magicclass_parent__ = ui
        self._widget._add_code_edit(native=True)
        now = datetime.now()
        self.append(Expr(Head.comment, [now.strftime("%Y/%m/%d %H:%M:%S")]))

    @property
    def widget(self) -> MacroEdit:
        """Returns the macro editor."""
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

    def get_command(self, key: int) -> Callable[[], Any]:
        """Get the command function at the give index."""
        action = self.widget._command_menu[key]
        return lambda: action.trigger()

    def get_evaluator(
        self,
        key: int | slice | Iterable[int],
        ns: dict[str, Any] = {},
    ) -> Callable[[], Any]:
        """Get the function that evaluate the macro lines at given indices."""
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


class DummyMacro(Macro):
    def insert(self, index, expr):
        pass
