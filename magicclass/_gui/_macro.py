from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, overload
from qtpy import QtWidgets as QtW, QtCore
from macrokit import Symbol, Expr, Head, Macro, parse
from magicgui.widgets import FileEdit

from magicclass.widgets import CodeEdit, TabbedContainer
from magicclass.utils import show_messagebox

if TYPE_CHECKING:
    from ._base import BaseGui
    from .mgui_ext import Clickable

# TODO: Tabs


class MacroEdit(TabbedContainer):
    """A text edit embeded with a custom menu bar."""

    window_count = 0

    def __init__(self, **kwargs):
        super().__init__(labels=False, **kwargs)
        self.native: QtW.QTabWidget
        self.__magicclass_parent__ = None
        self.native.setWindowTitle("Macro")
        self._native_macro = None
        self._set_menubar()

    def add_code_edit(self, native: bool = False) -> CodeEdit:
        from magicclass import defaults

        textedit = CodeEdit(name="macro")
        if native:
            if self._native_macro is not None:
                raise ValueError("Native macro already exists.")
            textedit.read_only = True
            self._native_macro = textedit
        self.append(textedit)
        if defaults["macro-highlight"]:
            textedit.syntax_highlight()
        return textedit

    @property
    def textedit(self) -> CodeEdit | None:
        """Return the current code editor"""
        wdt = self[self.current_index]
        if isinstance(wdt, CodeEdit):
            return wdt
        return None

    @property
    def native_macro(self) -> CodeEdit | None:
        return self._native_macro

    @property
    def value(self):
        """Get macro text."""
        return self.textedit.value

    @value.setter
    def value(self, value: str):
        self.textedit.value = value

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
        new = self.add_code_edit()
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
        from magicclass.utils import move_to_screen_center

        super().show()
        move_to_screen_center(self.native)

    def _execute(self, e=None):
        """Run macro."""
        self.execute()

    def _execute_selected(self, e=None):
        """Run selected line of macro."""
        parent = self._search_parent_magicclass()
        try:
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
        self._file_menu.addAction("Close", self._close, "Ctrl+W")

        self._tab_menu = QtW.QMenu("Tab", self.native)
        self._menubar.addMenu(self._tab_menu)
        self._tab_menu.addAction("New tab", self.new_tab, "Ctrl+T")
        self._tab_menu.addAction("Duplicate tab", self.duplicate_tab, "Ctrl+D")
        self._tab_menu.addAction("Delete tab", self.delete_tab, "Ctrl+W")

        # set macro menu
        self._macro_menu = QtW.QMenu("Macro", self.native)
        self._menubar.addMenu(self._macro_menu)

        self._macro_menu.addAction("Execute", self._execute, "Ctrl+F5")
        self._macro_menu.addAction(
            "Execute selected lines", self._execute_selected, "Ctrl+Shift+F5"
        )
        self._macro_menu.addSeparator()
        self._macro_menu.addAction(
            "Create", self._create_native_duplicate, "Ctrl+Shift+D"
        )


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
        if self._widget is None:
            self._widget = MacroEdit(name="Macro")
            self._widget.add_code_edit(native=True)
            from datetime import datetime

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
        if wdt := self.widget.native_macro:
            wdt.append(str(self.args[-1]))
        if len(self) > self._max_lines:
            del self[0]

    def _erase_last(self):
        if wdt := self.widget.native_macro:
            wdt.erase_last()
