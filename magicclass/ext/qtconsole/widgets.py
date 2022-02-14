from psygnal import Signal
from ...widgets.utils import FreeWidget


class QtConsole(FreeWidget):
    executed = Signal(str)

    def __init__(self, **kwargs):
        from ._qt import _Console

        super().__init__(**kwargs)

        self.console = _Console()
        self.set_widget(self.console)

    @property
    def __magicclass_parent__(self):
        """Return the parent UI object."""
        return self.console.parent_ui

    @__magicclass_parent__.setter
    def __magicclass_parent__(self, parent):
        while parent.__magicclass_parent__ is not None:
            parent = parent.__magicclass_parent__
        self.console.connect_parent(parent)

    @property
    def value(self) -> str:
        """Get current code block"""
        return self.console.input_buffer

    @value.setter
    def value(self, code: str) -> None:
        """Set code string to Jupyter QtConsole buffer"""
        self.console.input_buffer = ""
        if not isinstance(code, str):
            raise ValueError(f"Cannot set {type(code)}.")
        cursor = self.console._control.textCursor()
        lines = code.split("\n")
        for line in lines[:-1]:
            cursor.insertText(line + "\n")
            self.console._insert_continuation_prompt(cursor)  # insert "...:"
        cursor.insertText(lines[-1])

    def execute(self):
        """Execute current code block."""
        code = self.value
        self.console.execute()
        self.executed.emit(code)
