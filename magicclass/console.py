from ipykernel.connect import get_connection_file
from ipykernel.inprocess.ipkernel import InProcessInteractiveShell
from ipykernel.zmqshell import ZMQInteractiveShell
from IPython import get_ipython
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from qtconsole.client import QtKernelClient
from qtconsole.inprocess import QtInProcessKernelManager
from magicgui.events import Signal
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from magicgui.widgets import Widget
from .widgets import FrozenContainer

# See napari_console
# https://github.com/napari/napari-console

class _Console(RichJupyterWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def connect_parent(self, ui: Widget):
        if not isinstance(ui, Widget):
            raise TypeError(f"Cannot connect QtConsole to {type(ui)}.")
        
        shell = get_ipython()

        if shell is None:
            # If there is no currently running instance create an in-process
            # kernel.
            kernel_manager = QtInProcessKernelManager()
            kernel_manager.start_kernel(show_banner=False)
            kernel_manager.kernel.gui = 'qt'

            kernel_client = kernel_manager.client()
            kernel_client.start_channels()

            self.kernel_manager = kernel_manager
            self.kernel_client = kernel_client
            self.shell = kernel_manager.kernel.shell
            self.push = self.shell.push
        elif type(shell) == InProcessInteractiveShell:
            # If there is an existing running InProcessInteractiveShell
            # it is likely because multiple viewers have been launched from
            # the same process. In that case create a new kernel.
            # Connect existing kernel
            kernel_manager = QtInProcessKernelManager(kernel=shell.kernel)
            kernel_client = kernel_manager.client()

            self.kernel_manager = kernel_manager
            self.kernel_client = kernel_client
            self.shell = kernel_manager.kernel.shell
            self.push = self.shell.push
        elif isinstance(shell, TerminalInteractiveShell):
            # if launching from an ipython terminal then adding a console is
            # not supported. Instead users should use the ipython terminal for
            # the same functionality.
            self.kernel_client = None
            self.kernel_manager = None
            self.shell = None
            self.push = lambda var: None

        elif isinstance(shell, ZMQInteractiveShell):
            # if launching from jupyter notebook, connect to the existing
            # kernel
            kernel_client = QtKernelClient(
                connection_file=get_connection_file()
            )
            kernel_client.load_connection_file()
            kernel_client.start_channels()

            self.kernel_manager = None
            self.kernel_client = kernel_client
            self.shell = shell
            self.push = self.shell.push
        else:
            raise ValueError(
                'ipython shell not recognized; ' f'got {type(shell)}'
            )

        self.parent_ui = ui
        self.shell.push({"ui": ui})

        
class Console(FrozenContainer):
    executed = Signal(str)
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
        self.console.input_buffer = ""
        if not isinstance(code, str):
            raise ValueError(f"Cannot set {type(code)}.")
        cursor = self.console._control.textCursor()
        lines = code.split("\n")
        for line in lines[:-1]:
            cursor.insertText(line + "\n")
            self.console._insert_continuation_prompt(cursor) # insert "...:"
        cursor.insertText(lines[-1])
    
    def execute(self):
        """Execute current code block"""
        code = self.value
        self.console.execute()
        self.executed.emit(code)
        