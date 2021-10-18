from __future__ import annotations
from .core import magicclass, WidgetType
from ._base import BaseGui
from .field import field
from .macro import Identifier
from enum import Enum
from qtpy.QtGui import QFont, QTextOption
from magicgui.widgets import Container, TextEdit
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
            tooltip_ = field("")
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
            class GUI:
                """
                Your GUI looks like this!
                """
            @magicclass(labels=False)
            class Code:
                """
                A template of Python code is available here!
                """                
                txt = TextEdit()
                txt.native.setFont(QFont("Consolas"))
                def __post_init__(self):
                    self.txt.native.setParent(self.native, self.txt.native.windowFlags())
                    self.txt.native.setWordWrapMode(QTextOption.NoWrap)
        
        def Back_to_parent(self): ...
        def Reset(self): ...
    
    @Tools.Add_Container.wraps
    def append_(self):
        parent = self.Tools.Add_Container
        kwargs= dict(layout=parent.layout_.value.name, 
                     labels=parent.labels_.value,
                     name=parent.name_.value,
                     widget_type=parent.widget_type_.value.name
                     )
        @magicclass(**kwargs)
        class _container: pass
        kw = _dict_to_arguments(kwargs)
        if kw:
            kw = f"({kw})"
        self._code.append((f"@magicclass{kw}", self._indent))
        self._code.append((f"class {parent.name_.value}:", self._indent))
        self._indent += 4
        
        tooltip = parent.tooltip_.value
        if tooltip:
            self._code.append((f"\"\"\"{tooltip}\"\"\"", self._indent))
            
        widget = _container()
        
        if self._creation is None:
            self._creation = widget
            self.ViewPanel.Panels.GUI.append(self._creation)
        else:
            self._creation.append(widget)
            if isinstance(widget, BaseGui):
                widget.__magicclass_parent__ = self._creation
                self._creation = widget
                
        self._create_code()
        
    @Tools.Add_basic_widget.wraps
    def append_PushButton(self, function_name="", text="", tooltip=""):
        if function_name == "":
            raise ValueError("function name must be specified")
        if text:
            self._code.append((f"@set_design(text={text!r})", self._indent))
        else:
            text = function_name
                
        if tooltip:
            self._code.append((f"def {function_name}(self):", self._indent))
            self._code.append((f"\"\"\"{tooltip}\"\"\"", self._indent + 4))
        else:
            self._code.append((f"def {function_name}(self): ...", self._indent))
        
        fld = field(False, options={"text": text, "tooltip": tooltip}, widget_type="PushButton")
        self._creation.append(fld.to_widget())
        self._create_code()
        
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
        min = _as_scalar(min)
        max = _as_scalar(max)
        value = _as_scalar(value) if value else min
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
        min = _as_scalar(min)
        max = _as_scalar(max)
        value = _as_scalar(value) if value else min
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