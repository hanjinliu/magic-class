from __future__ import annotations
from pathlib import Path

from typing import TYPE_CHECKING, Any, Callable, Iterable, overload
import warnings
from datetime import datetime
from qtpy import QtWidgets as QtW, QtCore
from macrokit import Symbol, Expr, Head, BaseMacro, parse, symbol
from macrokit.utils import check_call_args, check_attributes
from magicgui.widgets import FileEdit, LineEdit, EmptyWidget, PushButton
from magicclass.utils.qthreading import thread_worker

from magicclass.widgets import CodeEdit, TabbedContainer, ScrollableContainer, Dialog
from magicclass.utils import move_to_screen_center
from magicclass.undo import ImplementsUndo, RedoAction, UndoCallback
from magicclass._gui.runner import CommandRunnerMenu

if TYPE_CHECKING:
    from ._base import BaseGui
    from .mgui_ext import Clickable


class MacroEdit(TabbedContainer):
    """A text edit embeded with a custom menu bar."""

    window_count = 0

    def __init__(self, is_main: bool = True, **kwargs):
        super().__init__(labels=False, **kwargs)
        self.native: QtW.QWidget
        self.__magicclass_parent__: BaseGui | None = None
        self.native.setWindowTitle("Macro")
        self.native_tab_widget.setTabBarAutoHide(True)
        # self.native_tab_widget.setTabsClosable(True)
        self._native_macro: CodeEdit | None = None
        self._recorded_macro: CodeEdit | None = None
        self._set_menubar(is_main=is_main)
        self._attribute_check = True
        self._signature_check = True
        self._name_check = True
        self._syntax_highlight = True

    def _add_code_edit(self, name: str = "script", native: bool = False) -> CodeEdit:
        """Add a new code edit widget as a new tab."""

        textedit = CodeEdit(name=name)
        if native:
            if self._native_macro is not None:
                raise ValueError("Native macro already exists.")
            textedit.read_only = True
            self._native_macro = textedit

        self.append(textedit)
        if self._syntax_highlight:
            qtextedit: QtW.QTextEdit = textedit.native
            # get background color
            bg = qtextedit.palette().color(qtextedit.backgroundRole())
            if sum(bg.getRgb()[:3]) > 255 * 3 / 2:
                textedit.syntax_highlight(theme="default")
            else:
                textedit.syntax_highlight(theme="native")
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

    def new_tab(self, name: str | None = None, text: str | None = None) -> CodeEdit:
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
        if text is not None:
            new.value = text
        return new

    def new_window(
        self, name: str | None = None, tabname: str | None = None
    ) -> MacroEdit:
        """
        Create a new window with same parent magic class widget.

        Parameters
        ----------
        name : str, optional
            Widget name. This name will be the title.
        tabname : str, optional
            Tab name. If not given, the tab name will be "script".

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
        if tabname is None:
            tabname = "macro"
        new._add_code_edit(name=tabname)
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
        was_visible = self.visible
        super().show()
        if not was_visible:
            move_to_screen_center(self.native)
        self.textedit.native.setFocus()

    def _execute(self, code: Expr):
        """Run macro."""
        parent = self._search_parent_magicclass()
        ns = {Symbol.var("ui"): parent}
        with parent._error_mode.raise_with_handler(self):
            if self._attribute_check:
                strs = [f"- {exc}" for exc in check_attributes(code, ns)]
                if strs:
                    raise AttributeError("Attribute check failed.\n" + "\n".join(strs))

            if self._signature_check:
                strs = [f"- {exc}" for exc in check_call_args(code, ns)]
                if strs:
                    raise AttributeError("Signature check failed.\n" + "\n".join(strs))

            if self._name_check:
                # TODO
                pass

            if str(code) == "":
                raise ValueError("No code selected")
            if (viewer := parent.parent_viewer) is not None:
                ns.setdefault(Symbol.var("viewer"), viewer)
            code.eval(ns)

    def _execute_selected(self, e=None):
        """Run selected line of macro."""
        self._execute(self.get_selected_expr())

    def execute_lines(self, indices: int | slice | Iterable[int]):
        """Execute given lines"""
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

    def _set_menubar(self, is_main: bool):
        self._menubar = QtW.QMenuBar(self.native)
        self.native.layout().setMenuBar(self._menubar)

        # fmt: off
        _file_menu = QtW.QMenu("File", self.native)
        _file_menu.setToolTipsVisible(True)
        self._menubar.addMenu(_file_menu)

        _file_menu.addAction(_action("New window", self._new_window, tooltip="Open a new macro editor", parent=_file_menu))
        _file_menu.addSeparator()
        _file_menu.addAction(_action("Open file", self._load, "Ctrl+O", tooltip="Open a python file", parent=_file_menu))
        _file_menu.addAction(_action("Save", self._save, "Ctrl+S", tooltip="Save the macro as a python file", parent=_file_menu))
        _file_menu.addSeparator()
        _file_menu.addAction(_action("Close", self._close, tooltip="Close this macro editor", parent=_file_menu))

        _tab_menu = QtW.QMenu("Tab", self.native)
        _tab_menu.setToolTipsVisible(True)
        self._menubar.addMenu(_tab_menu)
        _tab_menu.addAction(_action("New tab", self._new_tab, "Ctrl+T", tooltip="Open a new empty tab", parent=_tab_menu))
        _tab_menu.addAction(_action("Duplicate tab", self._duplicate_tab, "Ctrl+Shift+D", tooltip="Duplicate current tab as a new tab", parent=_tab_menu))
        _tab_menu.addAction(_action("Current macro in new tab", self._create_native_duplicate, tooltip="Duplicate current GUI macro in a new tab", parent=_tab_menu))
        _tab_menu.addAction(_action("Delete tab", self._delete_tab, "Ctrl+W", tooltip="Delete current tab", parent=_tab_menu))
        _tab_menu.addSeparator()
        _tab_menu.addAction(_action("Zoom in", self._zoom_in, "Ctrl+Shift+.", tooltip="Zoom in the text", parent=_tab_menu))
        _tab_menu.addAction(_action("Zoom out", self._zoom_out, "Ctrl+Shift+,", tooltip="Zoom out the text", parent=_tab_menu))


        # set macro menu
        _macro_menu = QtW.QMenu("Macro", self.native)
        _macro_menu.setToolTipsVisible(True)
        self._menubar.addMenu(_macro_menu)

        _macro_menu.addAction(_action("Execute", self.execute, "Ctrl+F5", tooltip="Execute the entire script of the current tab", parent=_macro_menu))
        _macro_menu.addAction(_action("Execute selected lines", self._execute_selected, "Ctrl+Shift+F5", tooltip="Execute the selected lines of the current tab", parent=_macro_menu))
        _macro_menu.addSeparator()
        if is_main:
            _action_start = _action("Start recording", self._start_recording, tooltip="Open a new tab and start recording GUI operations in it", parent=_macro_menu)
            _macro_menu.addAction(_action_start)
            _action_finish = _action("Finish recording", self._finish_recording, tooltip="Finish the recording task started by 'Start recording' menu", parent=_macro_menu)
            _macro_menu.addAction(_action_finish)
            _action_finish.setEnabled(False)
            _action_start.triggered.connect(lambda: _action_finish.setEnabled(True))
            _action_finish.triggered.connect(lambda: _action_finish.setEnabled(False))

        self._command_menu = CommandRunnerMenu(
            "Command",
            parent=self.native,
            magicclass_parent=self._search_parent_magicclass(),
        )
        self._command_menu.native.setToolTipsVisible(True)
        self._menubar.addMenu(self._command_menu.native)
        self._command_menu.native.addAction(_action("Create command", self._create_command, tooltip="Create a command using the selected lines", parent=self._command_menu.native))
        self._command_menu.native.addAction(_action("Rename command", self._rename_command, tooltip="Rename regeistered commands.", parent=self._command_menu.native))
        self._command_menu.native.addSeparator()
        # fmt: on


def _action(
    text: str,
    slot: Callable,
    shortcut: str | None = None,
    tooltip: str | None = None,
    parent=None,
):
    """Create a QAction object. Backend compatible."""
    action = QtW.QAction(text, parent=parent)
    action.triggered.connect(slot)
    if shortcut:
        action.setShortcut(shortcut)
    if tooltip:
        action.setToolTip(tooltip)
    return action


class PropertyGroup:
    def __init__(self, parent: GuiMacro | None = None):
        self._instances = dict[int, PropertyGroup]()
        self._parent = parent
        self._max_lines = 10000
        self._max_undo = 100

    def __get__(self, instance: GuiMacro, owner) -> PropertyGroup:
        if instance is None:
            return self
        return self._instances.setdefault(id(instance), self.__class__(parent=instance))

    @property
    def macro(self) -> GuiMacro:
        if self._parent is None:
            raise RuntimeError("This property group is not bound to any macro.")
        return self._parent

    @property
    def max_lines(self) -> int:
        return self._max_lines

    @max_lines.setter
    def max_lines(self, value: int):
        if value < 0:
            raise ValueError("max_lines must be >= 0")
        if value < len(self.macro):
            raise ValueError("max_lines must be larger than current number of lines")
        self._max_lines = value

    @property
    def max_undo(self) -> int:
        return self._max_undo

    @max_undo.setter
    def max_undo(self, value: int):
        if value < 0:
            raise ValueError("max_undo must be >= 0")
        if value < len(self.macro._stack_undo):
            raise ValueError(
                "max_undo must be larger than current number of undo steps"
            )
        self._max_undo = value

    @property
    def syntax_highlight(self) -> bool:
        return self.macro.widget._syntax_highlight

    @syntax_highlight.setter
    def syntax_highlight(self, value: bool):
        self.macro.widget._syntax_highlight = bool(value)

    @property
    def attribute_check(self) -> bool:
        return self.macro.widget._attribute_check

    @attribute_check.setter
    def attribute_check(self, value: bool):
        self.macro.widget._attribute_check = bool(value)

    @property
    def signature_check(self) -> bool:
        return self.macro.widget._signature_check

    @signature_check.setter
    def signature_check(self, value: bool):
        self.macro.widget._signature_check = bool(value)

    @property
    def name_check(self) -> bool:
        return self.macro.widget._name_check

    @name_check.setter
    def name_check(self, value: bool):
        self.macro.widget._name_check = bool(value)


class GuiMacro(BaseMacro):
    """Macro object with GUI-specific functions."""

    options = PropertyGroup()

    def __init__(self, ui: BaseGui = None, options: dict[str, Any] = {}):
        super().__init__()
        self.on_appended.append(self._on_macro_added)
        self.on_popped.append(self._on_macro_popped)

        self._widget = MacroEdit(name="Macro")
        self._widget.__magicclass_parent__ = ui
        self._widget._add_code_edit(native=True)
        now = datetime.now()
        self.append(Expr(Head.comment, [now.strftime("%Y/%m/%d %H:%M:%S")]))

        self._stack_undo: list[ImplementsUndo] = []
        self._stack_redo: list[tuple[Expr, ImplementsUndo]] = []
        self.options.max_lines = options.get("macro-max-history", 10000)
        self.options.max_undo = options.get("undo-max-history", 100)
        self.options.syntax_highlight = options.get("macro-highlight", False)
        self.options.attribute_check = options.get("macro-attribute-check", True)
        self.options.signature_check = options.get("macro-signature-check", True)
        self.options.name_check = options.get("macro-name-check", True)

    @property
    def widget(self) -> MacroEdit:
        """Returns the macro editor."""
        return self._widget

    @property
    def _gui_parent(self) -> BaseGui:
        """The parent GUI object."""
        return self.widget.__magicclass_parent__

    def clear_undo_stack(self) -> None:
        """Clear all the history of undo/redo."""
        self._stack_undo.clear()
        self._stack_redo.clear()

    def append_with_undo(self, expr: Expr, undo: UndoCallback) -> None:
        """Append an expression with its undo action."""
        if not isinstance(undo, UndoCallback):
            if callable(undo):
                undo = UndoCallback(undo)
            else:
                raise TypeError(f"undo must be callable, not {type(undo)}")
        self.append(expr)
        self._append_undo(undo)
        return None

    def _append_undo(self, undo: ImplementsUndo) -> None:
        self._stack_undo.append(undo)
        self._stack_redo.clear()
        if len(self._stack_undo) > self.options.max_undo:
            self._stack_undo.pop(0)
        return None

    def _pop_undo(self) -> ImplementsUndo:
        return self._stack_undo.pop()

    @property
    def undo_stack(self) -> dict[str, list[Expr]]:
        """Return a copy of undo stack info."""
        n_undo = len(self._stack_undo)
        if n_undo == 0:
            undo = []
        else:
            undo = [expr.copy() for expr in self.args[-n_undo:]]
        return dict(
            undo=undo,
            redo=[expr.copy() for expr, _ in self._stack_redo],
        )

    def undo(self):
        """Undo the last operation if undo is defined."""
        if len(self._stack_undo) == 0:
            return
        undo = self._stack_undo.pop()
        try:
            with self.blocked():
                undo.run()
        except Exception as e:
            self._stack_undo.append(undo)
            raise e
        else:
            expr = self.pop()
            self._stack_redo.append((expr, undo))

    def redo(self):
        """Redo the last undo operation."""
        if len(self._stack_redo) == 0:
            return
        if not self.active:
            raise ValueError("Cannot redo when the macro is blocked.")
        expr, undo = self._stack_redo.pop()
        try:
            redo_action = undo.redo_action
            if redo_action.matches("default"):
                ns = {self._gui_parent._my_symbol: self._gui_parent}
                parent = self._gui_parent
                if (viewer := parent.parent_viewer) is not None:
                    ns.setdefault(Symbol.var("viewer"), viewer)
                with self.blocked():
                    expr.eval(ns)
            elif redo_action.matches("custom"):
                redo_action: RedoAction.Custom
                with self.blocked():
                    redo_action.run()
            else:
                raise ValueError(f"Redo is not defined for {undo}")
        except Exception as e:
            self._stack_redo.append((expr, undo))
            raise e
        else:
            self.append(expr)
            self._stack_undo.append(undo)

    def copy(self) -> BaseMacro:
        """Copy the macro instance."""
        # GuiMacro does not support deepcopy (and apparently _widget should not be copied)
        from copy import deepcopy

        return BaseMacro(deepcopy(self.args))

    @overload
    def __getitem__(self, key: int) -> Expr:
        ...

    @overload
    def __getitem__(self, key: slice) -> BaseMacro:
        ...

    def __getitem__(self, key):
        if isinstance(key, slice):
            return BaseMacro(self._args)[key]
        return super().__getitem__(key)

    def subset(self, indices: Iterable[int]) -> BaseMacro:
        """Generate a subset of macro."""
        args = [self._args[i] for i in indices]
        return BaseMacro(args)

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
        self,
        index: int = -1,
        *,
        same_args: bool = False,
        blocking: bool = True,
        raise_parse_error: bool = True,
        check_nargs: bool = False,
    ) -> None:
        """
        Repeat the method call at the given index.

        Parameters
        ----------
        index : int, default is -1
            Index of the method call to repeat.
        same_args : bool, default is False
            If True, method will be called with the same arguments as before. Otherwise,
            magicgui widget will be opened.
        blocking : bool, default is True
            If True, the method will be called in blocking mode if it is a thread worker.
            Note that programatically calling "repeat_method" in non-blocking mode will
            cause unexpected macro recording.
        check_nargs : bool, default is False
            If False, the method will be called even if it has no arguments. Otherwise,
            raise ValueError. This option is useful to avoid calling long-running commands.
        """
        try:
            _object, _args, _kwargs = self[index].split_call()
            _ui, *_attributes, _last = _object.split_getattr()
        except ValueError as e:
            if raise_parse_error:
                raise e
            else:
                return None
        ui = self._gui_parent
        assert _ui == ui._my_symbol
        ins = ui
        for attr in _attributes:
            ins = getattr(ins, attr.name)

        wdt: Clickable = ins[_last.name]
        if wdt.mgui is None:
            # If macro is added by users, the internal magicgui will not be tagged
            # to the button. Create one here.
            from ._base import _build_mgui, _create_gui_method

            func = _create_gui_method(ui, getattr(ins, _last.name))
            wdt.mgui = _build_mgui(wdt, func, ui)

        if check_nargs and not same_args:
            n_widget_args = sum(
                not isinstance(w, EmptyWidget)
                for w in wdt.mgui
                if not isinstance(w, PushButton)
            )
            if n_widget_args == 0:
                raise ValueError(f"Method {_object} does not have any arguments.")

        if not blocking:
            if same_args:
                _args, _kwargs = self[index].eval_call_args({symbol(ui): ui})
                _input = wdt.mgui.__signature__.bind_partial(_args, _kwargs).arguments
                with wdt.mgui.changed.blocked():
                    wdt.mgui.update(**_input)
                wdt.mgui.call_button.changed()  # click the call button
            else:
                wdt.changed()  # click the button to open magicgui
        else:
            if same_args:
                self[index].eval({symbol(ui): ui})  # call the method
            else:
                if isinstance(wdt.mgui._function, thread_worker):
                    raise ValueError(
                        "same_args=False is not supported for blocking=True."
                    )
                wdt.changed()  # save as blocking=False for non-thread worker
        return None

    def _on_macro_added(self, expr=None):
        line = str(self.args[-1])
        if wdt := self.widget.native_macro:
            wdt.append(line)
        if wdt := self.widget.recorded_macro:
            wdt.append(line)
        if len(self) > self.options.max_lines:
            del self[0]

    def _on_macro_popped(self, expr=None):
        self._erase_last()

    def _erase_last(self):
        if wdt := self.widget.native_macro:
            wdt.erase_last()
        if wdt := self.widget.recorded_macro:
            wdt.erase_last()


class DummyMacro(BaseMacro):
    def insert(self, index, expr):
        pass

    def _append_undo(self, undo) -> None:
        return None

    def _pop_undo(self) -> None:
        return None

    def clear_undo_stack(self) -> None:
        return None
