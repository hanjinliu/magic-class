from ipykernel.connect import get_connection_file
from IPython import get_ipython
from qtconsole.client import QtKernelClient
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from magicgui.widgets import Widget
from .widgets import FrozenContainer

class _Console(RichJupyterWidget):
    def connect_parent(self, ui: Widget):
        if not isinstance(ui, Widget):
            raise TypeError(f"Cannot connect QtConsole to {type(ui)}.")
        self.parent_ui = ui
        self.shell = get_ipython()
        connection_file = get_connection_file()
        kernel_client = QtKernelClient(connection_file=connection_file)
        kernel_client.load_connection_file()
        kernel_client.start_channels()
        self.kernel_manager = None
        self.kernel_client = kernel_client
        self.shell.push({"ui": ui})
    

class Console(FrozenContainer):
    def __init__(self, **kwargs):
        super().__init__(labels=False, **kwargs)
        self.console = _Console()
        self.set_widget(self.console)
    
    @property
    def __magicclass_parent__(self):
        return self.console.parent_ui
    
    @__magicclass_parent__.setter
    def __magicclass_parent__(self, parent):
        self.console.connect_parent(parent)
    
    @property
    def value(self) -> str:
        """Get current code block"""
        return self.console.input_buffer
    
    @value.setter
    def value(self, code: str) -> None:
        """Set code string to Jupyter QtConsole buffer"""
        if not isinstance(code, str):
            raise ValueError("Cannot set code ")
        cursor = self.console._control.textCursor()
        lines = code.split("\n")
        for line in lines[:-1]:
            cursor.insertText(line + "\n")
            self.console._insert_continuation_prompt(cursor) # insert "...:"
        cursor.insertText(lines[-1])
    
    def execute(self):
        """Execute current code block"""
        self.console.execute()