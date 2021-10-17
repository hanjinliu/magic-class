from __future__ import annotations
from .core import magicclass, WidgetType
from ._base import BaseGui
from .field import field
from .macro import Identifier
from enum import Enum
from qtpy.QtGui import QFont
from magicgui.widgets import Container, Label, TextEdit
import numpy as np

class Layout(Enum):
    vertical = 0
    horizontal = 1

@magicclass(labels=False, layout="horizontal", widget_type=WidgetType.split)
class MagicClassCreator:
    def __post_init__(self):
        self.code_block = self.ViewPanel.Panels.Code.txt
        self.Reset()
        w0 = self.width/2
        self.Tools.width = self.ViewPanel.width = w0
        
    @magicclass(widget_type=WidgetType.tabbed)
    class Tools:
        @magicclass
        class Add_Container:
            layout_ = field(Layout)
            labels_ = field(True)
            name_ = field("Gui")
            widget_type_ = field(WidgetType)
            
            def append_(self): ...
        
        @magicclass
        class Add_basic_widget:
            def append_PushButton(self): ...
            def append_LineEdit(self): ...
            def append_CheckBox(self): ...
            def append_SpinBox(self): ...
            def append_Slider(self): ...
            def append_Label(self): ...
            def append_Table(self): ...
    
    
    @magicclass
    class ViewPanel:
        @magicclass(labels=False, widget_type="tabbed")
        class Panels:
            @magicclass(labels=False)
            class GUI: pass
            @magicclass(labels=False)
            class Code:
                txt = TextEdit()
                txt.native.setFont(QFont("Consolas"))
                def __post_init__(self):
                    self.txt.native.setParent(self.native, self.txt.native.windowFlags())
        
        def Back_to_parent(self): ...
        def Reset(self): ...
    
    @Tools.Add_Container.wraps
    def append_(self):
        widget = self._to_container()
        if self._creation is None:
            self._creation = widget
            self.ViewPanel.Panels.GUI.append(self._creation)
        else:
            self._creation.append(widget)
            if isinstance(widget, BaseGui):
                self._creation = widget
        self._create_code()
        
    def _to_container(self):
        parent = self.Tools.Add_Container
        kwargs= dict(layout=parent.layout_.value.name, 
                     labels=parent.labels_.value,
                     name=parent.name_.value,
                     widget_type=parent.widget_type_.value.name
                     )
        @magicclass(**kwargs)
        class _container:
            """Created by magicclass creator"""
        kw = _dict_to_arguments(kwargs)
        if kw:
            kw = f"({kw})"
        self._code.append((f"@magicclass{kw}", self._indent))
        self._code.append((f"class {parent.name_.value}:", self._indent))
        self._indent += 4
        return _container()
    
    @Tools.Add_basic_widget.wraps
    def append_PushButton(self, text="", tooltip=""):
        self._append_widget(False, 
                            {"text": text, "tooltip": tooltip}, 
                            widget_type="PushButton")
        
    @Tools.Add_basic_widget.wraps
    def append_LineEdit(self, label_="", value="", tooltip=""):
        label = label_ or None
        self._append_widget(value, {"label": label, "tooltip": tooltip})
    
    @Tools.Add_basic_widget.wraps
    def append_CheckBox(self, label_="", checked=False, tooltip=""):
        label = label_ or None
        self._append_widget(checked, {"label": label, "tooltip": tooltip})
    
    @Tools.Add_basic_widget.wraps
    def append_SpinBox(self, label_="", value="", min="0", max="1000", step="1", tooltip=""):
        label = label_ or None
        value = _as_scalar(value)
        min = _as_scalar(min)
        max = _as_scalar(max)
        step = _as_scalar(step)
        if value < min:
            min = value
        elif value > max:
            max = value
        self._append_widget(value, 
                            {"label": label, "min": min, "max": max, "step": step, "tooltip": tooltip})
    
    @Tools.Add_basic_widget.wraps
    def append_Slider(self, label_="", value="", min="0", max="1000", step="1", tooltip=""):
        label = label_ or None
        value = _as_scalar(value)
        min = _as_scalar(min)
        max = _as_scalar(max)
        step = _as_scalar(step)
        if value < min:
            min = value
        elif value > max:
            max = value
        widget = "FloatSlider" if isinstance(value, float) else "Slider"
        self._append_widget(value, 
                            {"label": label, "min": min, "max": max, "step": step, "tooltip": tooltip}, 
                            widget_type=widget)
    
    @Tools.Add_basic_widget.wraps
    def append_Label(self, label_="", tooltip=""):
        self._append_widget(label_, 
                            {"tooltip": tooltip},
                            widget_type="Label")
    
    @Tools.Add_basic_widget.wraps
    def append_Table(self, label_="", n_rows=4, n_columns=3, tooltip=""):
        data = np.zeros((n_rows, n_columns), dtype="<U32")
        self._append_widget(data, 
                            {"tooltip": tooltip, "label": label_},
                            widget_type="Table")
    
    def _append_widget(self, value, options=None, **kwargs):
        if options is None:
            options = {}
        fld = field(value, options=options, **kwargs)
        kw = _dict_to_arguments(kwargs)
        code = f"f{self._nfield} = field({Identifier(value)}, options={options}, {kw})"
        self._code.append((code, self._indent))
        self._creation.append(fld.to_widget())
        self._create_code()
        self._nfield += 1
        
    def _create_code(self):
        out = []
        for code, ind in self._code:
            out.append(" "*ind + code)
        out = "\n".join(out)
        self.code_block.value = out
    
    @ViewPanel.wraps    
    def Back_to_parent(self):
        if self._creation.__magicclass_parent__ is None:
            raise ValueError("No more parent!")
        self._creation = self._creation.__magicclass_parent__
        self._indent -= 4
    
    @ViewPanel.wraps    
    def Reset(self):
        self._creation: None | BaseGui | Container = None
        self._code: list[str] = []
        self._nfield: int = 0
        self._indent: int = 0
        self.ViewPanel.Panels.GUI.clear()
        self.code_block.value = ""

def _as_scalar(value: str):
    try:
        value = int(value)
    except ValueError:
        value = float(value)
    return value

def _dict_to_arguments(kwargs: dict):
    return ", ".join(f"{k}={Identifier(v)}" for k, v in kwargs.items())