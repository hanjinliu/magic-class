from __future__ import annotations
import inspect
from enum import Enum
from typing import Callable, Any, TYPE_CHECKING
from docstring_parser import parse
from qtpy.QtWidgets import QApplication, QMessageBox

if TYPE_CHECKING:
    from magicgui.widgets import FunctionGui

__all__ = ["MessageBoxMode", "show_messagebox", "open_url", "screen_center"]

def iter_members(cls: type, exclude_prefix: str = "__") -> list[str, Any]:
    """
    Iterate over all the members in the order of source code line number. 
    This function is identical to inspect.getmembers except for the order
    of the results. We have to sort the name in the order of line number.
    """    
    mro = (cls,) + inspect.getmro(cls)
    processed = set()
    names: list[str] = list(cls.__dict__.keys())
    try:
        for base in mro:
            for k in base.__dict__.keys():
                if k not in names:
                    names.append(k)
                    
    except AttributeError:
        pass
    
    for key in names:
        try:
            value = getattr(cls, key)
            # handle the duplicate key
            if key in processed:
                raise AttributeError
        except AttributeError:
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            else:
                continue
        if not key.startswith(exclude_prefix):
            yield key, value
        processed.add(key)
    

def extract_tooltip(obj: Any) -> str:
    if not hasattr(obj, "__doc__"):
        return ""
    
    doc = parse(obj.__doc__)
    if doc.short_description is None:
        return ""
    elif doc.long_description is None:
        return doc.short_description
    else:
        return doc.short_description + "\n" + doc.long_description


def get_parameters(fgui: FunctionGui):
    return {k: v.default for k, v in fgui.__signature__.parameters.items()}

def get_signature(func):
    """
    Similar to ``inspect.signature`` but safely returns ``MagicMethodSignature``.
    """    
    if hasattr(func, "__signature__"):
        sig = func.__signature__
    else:
        sig = inspect.signature(func)
    return sig


def define_callback(self, callback: Callable):
    clsname, funcname = callback.__qualname__.split(".")
    def _callback():
        # search for parent instances that have the same name.
        current_self = self
        while not (hasattr(current_self, funcname) and 
                   current_self.__class__.__name__ == clsname):
            current_self = current_self.__magicclass_parent__
        getattr(current_self, funcname)()
        return None
    return _callback


class InvalidMagicClassError(Exception):
    """
    This exception will be raised when class definition is not a valid magic-class.
    """    

class MessageBoxMode(Enum):
    ERROR = "error"
    WARNING = "warn"
    INFO = "info"
    QUESTION = "question"
    ABOUT = "about"

_QMESSAGE_MODES = {
    MessageBoxMode.ERROR: QMessageBox.critical,
    MessageBoxMode.WARNING: QMessageBox.warning,
    MessageBoxMode.INFO: QMessageBox.information,
    MessageBoxMode.QUESTION: QMessageBox.question,
    MessageBoxMode.ABOUT: QMessageBox.about,
}

def show_messagebox(mode: str | MessageBoxMode = MessageBoxMode.INFO,
                    title: str = None,
                    text: str = None,
                    parent=None
                    ) -> bool:
    """
    Freeze the GUI and open a messagebox dialog.

    Parameters
    ----------
    mode : str or MessageBoxMode, default is MessageBoxMode.INFO
        Mode of message box. Must be "error", "warn", "info", "question" or "about".
    title : str, optional
        Title of messagebox.
    text : str, optional
        Text in messagebox.
    parent : QWidget, optional
        Parent widget.

    Returns
    -------
    bool
        If "OK" or "Yes" is clicked, return True. Otherwise return False.
    """    
    show_dialog = _QMESSAGE_MODES[MessageBoxMode(mode)]
    result = show_dialog(parent, title, text)
    return result in (QMessageBox.Ok, QMessageBox.Yes)

def open_url(link: str) -> None:
    """
    Open the link with the default browser.

    Parameters
    ----------
    link : str
        Link to the home page.
    """    
    from qtpy.QtGui import QDesktopServices
    from qtpy.QtCore import QUrl
    QDesktopServices.openUrl(QUrl(link))

def to_clipboard(obj: Any) -> None:
    """
    Copy an object of any type to the clipboard.
    You can copy text, ndarray as an image or data frame as a table data.

    Parameters
    ----------
    obj : Any
        Object to be copied.
    """    
    from qtpy.QtGui import QGuiApplication, QImage
    import numpy as np
    import pandas as pd
    clipboard = QGuiApplication.clipboard()
    if isinstance(obj, str):
        clipboard.setText(obj)
    elif isinstance(obj, np.ndarray):
        clipboard.setImage(QImage(obj))
    elif isinstance(obj, pd.DataFrame):
        clipboard.setText(obj.to_csv())
    else:
        clipboard.setText(str(obj))
        
def screen_center():
    """
    Get the center coordinate of the screen.
    """    
    return QApplication.desktop().screen().rect().center()