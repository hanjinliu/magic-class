from __future__ import annotations
from typing import Callable, Iterable
import warnings
from inspect import signature
from collections.abc import MutableSequence
from magicgui.events import Signal
from magicgui.widgets import Image, Table, Label, FunctionGui
from magicgui.application import use_app
from magicgui.widgets._bases import ButtonWidget
from magicgui.widgets._bases.widget import Widget
from macrokit import Symbol
from qtpy.QtWidgets import QMenu

from .mgui_ext import AbstractAction, Action, WidgetAction, _LabeledWidgetAction
from ._base import BaseGui, PopUpMode, ErrorMode, value_widget_callback, nested_function_gui_callback
from .utils import define_callback, MagicClassConstructionError

from ..signature import get_additional_option
from ..fields import MagicField
from ..widgets import Separator, FreeWidget
from ..utils import iter_members

def _check_popupmode(popup_mode: PopUpMode):
    if popup_mode in (PopUpMode.above, PopUpMode.below, PopUpMode.first):
        msg = f"magicmenu does not support popup mode {popup_mode.value}."\
                "PopUpMode.popup is used instead"
        warnings.warn(msg, UserWarning)
    elif popup_mode == PopUpMode.last:
        msg = f"magicmenu does not support popup mode {popup_mode.value}."\
                "PopUpMode.parentlast is used instead"
        warnings.warn(msg, UserWarning)
        popup_mode = PopUpMode.parentlast
    
    return popup_mode

class MenuGuiBase(BaseGui, MutableSequence):
    _component_class = Action
    changed = Signal(object)
    
    def __init__(self, 
                 parent=None, 
                 name: str = None,
                 close_on_run: bool = None,
                 popup_mode: str|PopUpMode = None,
                 error_mode: str|ErrorMode = None,
                 labels: bool = True
                 ):
        popup_mode = _check_popupmode(popup_mode)
            
        super().__init__(close_on_run=close_on_run, popup_mode=popup_mode, error_mode=error_mode)
        name = name or self.__class__.__name__
        self.native = QMenu(name, parent)
        self.native.setToolTipsVisible(True)
        self.native.setObjectName(self.__class__.__name__)
        self.name = name
        self._list: list[MenuGuiBase | AbstractAction] = []
        self.labels = labels
        
    @property
    def parent(self):
        return self.native.parent()

    def _create_widget_from_field(self, name: str, fld: MagicField):
        cls = self.__class__
        if fld.not_ready():
            try:
                fld.default_factory = cls.__annotations__[name]
                if isinstance(fld.default_factory, str):
                    # Sometimes annotation is not type but str. 
                    from pydoc import locate
                    fld.default_factory = locate(fld.default_factory)
                    
            except (AttributeError, KeyError):
                pass
            
        fld.name = fld.name or name.replace("_", " ")
        action = fld.get_action(self)
            
        if action.support_value:
            # If the field has callbacks, connect it to the newly generated widget.
            for callback in fld.callbacks:
                # funcname = callback.__name__
                action.changed.connect(define_callback(self, callback))
                     
            # By default, set value function will be connected to the widget.
            if fld.record:
                f = value_widget_callback(self, action, name, getvalue=type(fld) is MagicField)
                action.changed.connect(f)
                
        return action
    
    def _convert_attributes_into_widgets(self):
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            self.native.setToolTip(cls.__doc__)
            
        # Bind all the methods and annotations
        base_members = set(x[0] for x in iter_members(MenuGuiBase))        
        
        _hist: list[tuple[str, str, str]] = [] # for traceback
        
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            try:
                if isinstance(attr, type):
                    # Nested magic-menu
                    widget = attr()
                    setattr(self, name, widget)
                
                elif isinstance(attr, MagicField):
                    widget = self._create_widget_from_field(name, attr)
                    
                else:
                    # convert class method into instance method
                    widget = getattr(self, name, None)
                    
                if name.startswith("_"):
                    continue
                
                if isinstance(widget, FunctionGui):
                    p0 = list(signature(attr).parameters)[0]
                    getattr(widget, p0).bind(self) # set self to the first argument
                    # magic-class has to know when the nested FunctionGui is called.
                    f = nested_function_gui_callback(self, widget)
                    widget.called.connect(f)
                    
                if isinstance(widget, (MenuGuiBase, AbstractAction, Widget, Callable)):
                    if (not isinstance(widget, Widget)) and callable(widget):
                        widget = self._create_widget_from_method(widget)
                    
                    elif hasattr(widget, "__magicclass_parent__") or \
                        hasattr(widget.__class__, "__magicclass_parent__"):
                        if isinstance(widget, BaseGui):
                            widget._my_symbol = Symbol(name)
                        # magic-class has to know its parent.
                        # if __magicclass_parent__ is defined as a property, hasattr must be called
                        # with a type object (not instance).
                        widget.__magicclass_parent__ = self
                        
                    clsname = get_additional_option(attr, "into")
                    if clsname is not None:
                        self._unwrap_method(clsname, name, widget)
                    else:           
                        self.append(widget)
                    
                    _hist.append((name, str(type(attr)), type(widget).__name__))
            
            except Exception as e:
                hist_str = "\n\t".join(map(
                    lambda x: f"{x[0]} {x[1]} -> {x[2]}",
                    _hist
                    )) + f"\n\t\t{name} ({type(attr).__name__}) <--- Error"
                if not hist_str.startswith("\n\t"):
                    hist_str = "\n\t" + hist_str
                if isinstance(e, MagicClassConstructionError):
                    e.args = (f"\n{hist_str}\n{e}",)
                    raise e
                else:
                    raise MagicClassConstructionError(f"{hist_str}\n\n{type(e).__name__}: {e}") from e
        
        return None
    
    def __getitem__(self, key: int|str) -> MenuGuiBase | AbstractAction:
        if isinstance(key, int):
            return self._list[key]
        
        out = None
        for obj in self._list:
            if obj.name == key:
                out = obj
                break
        if out is None:
            raise KeyError(key)
        return out
    
    def __setitem__(self, key, value):
        raise NotImplementedError()
    
    def __delitem__(self, key: int | str) -> None:
        self.native.removeAction(self[key].native)
    
    def __iter__(self) -> Iterable[MenuGuiBase | AbstractAction]:
        return iter(self._list)
    
    def __len__(self) -> int:
        return len(self._list)
    
    def append(self, obj: Callable | MenuGuiBase | AbstractAction | Widget) -> None:
        return self.insert(len(self._list), obj)
    
    def insert(self, key: int, obj: Callable | MenuGuiBase | AbstractAction | Widget) -> None:
        """
        Insert object into the menu. Could be widget or callable.

        Parameters
        ----------
        key : int
            Position to insert.
        obj : Callable | MenuGuiBase | AbstractAction | Widget
            Object to insert.
        """        
        if isinstance(obj, self._component_class):
            _insert(self.native, key, obj.native)
            self._list.insert(key, obj)
        elif isinstance(obj, Separator):
            _insert(self.native, key, "sep")
            self._list.insert(key, obj)
        elif isinstance(obj, Widget):
            waction = WidgetAction(obj, name=obj.name, parent=self.native)
            if isinstance(obj, BaseGui):
                obj.__magicclass_parent__ = self
            self.insert(key, waction)
        elif isinstance(obj, WidgetAction):
            if isinstance(obj.widget, Separator):
                self.insert(key, obj.widget)
            else:
                _hide_labels = (_LabeledWidgetAction, ButtonWidget, FreeWidget, Label, 
                                FunctionGui, Image, Table)
                _obj = obj
                if not isinstance(obj.widget, _hide_labels):
                    _obj = _LabeledWidgetAction.from_action(obj)
                _obj.parent = self
                _insert(self.native, key, _obj.native)
                self._unify_label_widths()
                self._list.insert(key, obj)
        elif isinstance(obj, MenuGuiBase):
            obj.__magicclass_parent__ = self
            _insert(self.native, key, obj.native)
            self._list.insert(key, obj)
            self.__magicclass_children__.insert(key, obj)
            obj.native.setParent(self.native, obj.native.windowFlags())
        else:
            raise TypeError(f"{type(obj)} is not supported.")
    
    def _unify_label_widths(self):
        _hide_labels = (_LabeledWidgetAction, ButtonWidget, FreeWidget, Label, FunctionGui,
                        Image, Table, Action)
        need_labels = [w for w in self if not isinstance(w, _hide_labels)]
        
        if self.labels and need_labels:
            measure = use_app().get_obj("get_text_width")
            widest_label = max(measure(w.label) for w in need_labels)
            for w in need_labels:
                labeled_widget = w._labeled_widget()
                if labeled_widget:
                    labeled_widget.label_width = widest_label

    def render(self):
        try:
            import numpy as np
        except ImportError:
            raise ModuleNotFoundError(
                "could not find module 'numpy'. "
                "Please `pip install numpy` to render widgets."
            ) from None
        import qtpy
        img = self.native.grab().toImage()
        bits = img.constBits()
        h, w, c = img.height(), img.width(), 4
        if qtpy.API_NAME == "PySide2":
            arr = np.array(bits).reshape(h, w, c)
        else:
            bits.setsize(h * w * c)
            arr = np.frombuffer(bits, np.uint8).reshape(h, w, c)

        return arr[:, :, [2, 1, 0, 3]]

    def _repr_png_(self):
        """Return PNG representation of the widget for QtConsole."""
        from io import BytesIO

        try:
            from imageio import imsave
        except ImportError:
            print(
                "(For a nicer magicmenu widget representation in "
                "Jupyter, please `pip install imageio`)"
            )
            return None

        with BytesIO() as file_obj:
            imsave(file_obj, self.render(), format="png")
            file_obj.seek(0)
            return file_obj.read()

def _insert(qmenu: QMenu, key: int, obj):
    """
    Insert a QObject into a QMenu in a Pythonic way, like qmenu.insert(key, obj).

    Parameters
    ----------
    qmenu : QMenu
        QMenu object to which object will be inserted.
    key : int
        Position to insert.
    obj : QMenu or QAction or "sep"
        Object to be inserted.
    """    
    actions = qmenu.actions()
    l = len(actions)
    if key < 0:
        key = key + l
    if key == l:
        if isinstance(obj, QMenu):
            qmenu.addMenu(obj)
        elif obj == "sep":
            qmenu.addSeparator()
        else:
            qmenu.addAction(obj)
    else:
        new_action = actions[key]
        before = new_action
        if isinstance(obj, QMenu):
            qmenu.insertMenu(before, obj)
        elif obj == "sep":
            qmenu.insertSeparator(before)
        else:
            qmenu.insertAction(before, obj)
        
    
class MenuGui(MenuGuiBase):
    """Magic class that will be converted into a menu bar."""

class ContextMenuGui(MenuGuiBase):
    """Magic class that will be converted into a context menu."""
    # TODO: Prevent more than one context menu
