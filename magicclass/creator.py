from __future__ import annotations
from .core import magicclass, WidgetType
from ._base import BaseGui
from .field import field
from .macro import Symbol
from .widgets import ConsoleTextEdit
from enum import Enum
from magicgui.widgets import Container
from magicgui.types import FileDialogMode
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
    
    @property
    def gui(self):
        return self.ViewPanel.Panels.GUI[0]
        
    @magicclass(widget_type=WidgetType.tabbed)
    class Tools:
        @magicclass
        class Add_Container:
            layout_ = field(Layout)
            labels_ = field(True)
            name_ = field("Gui")
            tooltip_ = field("")
            widget_type_ = field(WidgetType)
            
            @magicclass(widget_type="collapsible")
            class Others:
                close_on_run_ = field(True)
                popup_ = field(True)
                
            def append_(self): ...
        
        @magicclass
        class Add_basic_widget:
            def append_PushButton(self): ...
            def append_LineEdit(self): ...
            def append_CheckBox(self): ...
            def append_SpinBox(self): ...
            def append_Slider(self): ...
            def append_Label(self): ...
            def append_FileEdit(self): ...
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
                txt = ConsoleTextEdit(name="code")
        
        def Back_to_parent(self): ...
        def Remove_last_widget(self): ...
        def Reset(self): ...
    
    @Tools.Add_Container.wraps
    def append_(self):
        parent = self.Tools.Add_Container
        kwargs= dict(layout=parent.layout_.value.name, 
                     labels=parent.labels_.value,
                     name=parent.name_.value,
                     widget_type=parent.widget_type_.value.name,
                     close_on_run=parent.Others.close_on_run_.value,
                     popup=parent.Others.popup_.value,
                     )
        
        name = parent.name_.value
        if hasattr(self._current_container, name):
            raise ValueError(f"Name collision: {name}")
        elif name == "":
            raise ValueError("Name is not set.")
        
        @magicclass(**kwargs)
        class _container: pass
        kw = _dict_to_arguments(kwargs)
        if kw:
            kw = f"({kw})"
        _code_list = []
        _code_list.append((f"@magicclass{kw}", self._indent))
        _code_list.append((f"class {parent.name_.value}:", self._indent))
        self._indent += 4
        
        tooltip = parent.tooltip_.value
        if tooltip:
            _code_list.append((f"\"\"\"{tooltip}\"\"\"", self._indent))
            
        widget = _container()
        
        if self._current_container is None:
            self._current_container = widget
            self.ViewPanel.Panels.GUI.append(self._current_container)
        else:
            self._current_container.append(widget)
            if isinstance(widget, BaseGui):
                widget.__magicclass_parent__ = self._current_container
                self._current_container = widget
        
        self._code.append(_code_list)
        self._create_code()
        
    @Tools.Add_basic_widget.wraps
    def append_PushButton(self, function_name="", text="", tooltip=""):
        """Append PushButton widget by function definition."""
        if function_name == "":
            raise ValueError("function name must be specified")
        elif hasattr(self._current_container, function_name):
            raise ValueError(f"Name collision: {function_name}")
        
        _code_list = []
        
        if text:
            _code_list.append((f"@set_design(text={text!r})", self._indent))
        else:
            text = function_name
                
        if tooltip:
            _code_list.append((f"def {function_name}(self):", self._indent))
            _code_list.append((f"\"\"\"{tooltip}\"\"\"", self._indent + 4))
        else:
            _code_list.append((f"def {function_name}(self): ...", self._indent))
        
        
        fld = field(False, options={"text": text, "tooltip": tooltip}, widget_type="PushButton")
        self._current_container.append(fld.to_widget())
        self._code.append(_code_list)
        self._create_code()
        
    @Tools.Add_basic_widget.wraps
    def append_LineEdit(self, label_="", value="", tooltip=""):
        """Append LineEdit widget."""
        label = label_ or None
        self._append_widget(value, {"label": label, "tooltip": tooltip})
    
    @Tools.Add_basic_widget.wraps
    def append_CheckBox(self, label_="", checked=False, tooltip=""):
        """Append CheckBox widget."""
        label = label_ or None
        self._append_widget(checked, {"label": label, "tooltip": tooltip})
    
    @Tools.Add_basic_widget.wraps
    def append_SpinBox(self, label_="", value="", min="0", max="1000", step="1", tooltip=""):
        """Append SpinBox or FloatSpinBox widget."""
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
        """Append Slider or FloatSlider widget."""
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
        """Append Label widget."""
        self._append_widget(label_, 
                            {"tooltip": tooltip},
                            widget_type="Label")
    
    @Tools.Add_basic_widget.wraps
    def append_FileEdit(self, label_="", mode=FileDialogMode.EXISTING_FILE, tooltip=""):
        """Append FileEdit widget."""
        self._append_widget(".", 
                            {"mode": mode, "tooltip": tooltip, "label": label_},
                            widget_type="FileEdit")
    
    @Tools.Add_basic_widget.wraps
    def append_Table(self, label_="", n_rows=4, n_columns=3, read_only=False, tooltip=""):
        """Append Table widget."""
        data = np.zeros((n_rows, n_columns), dtype="<U32")
        self._append_widget(data, 
                            {"tooltip": tooltip, "label": label_},
                            widget_type="Table")
        if read_only:
            self._current_container[-1].read_only = True
    
    def _append_widget(self, value, options=None, **kwargs):
        if options is None:
            options = {}
        fld = field(value, options=options, **kwargs)
        kw = _dict_to_arguments(kwargs)
        code = f"f{self._nfield} = field({Symbol(value)}, options={options}, {kw})"
        self._code.append([(code, self._indent)])
        self._current_container.append(fld.to_widget())
        self._create_code()
        self._nfield += 1
        
    def _create_code(self):
        out = []
        for code in self._code:
            for line, ind in code:
                out.append(" "*ind + line)
        out = "\n".join(out)
        self.code_block.value = out
    
    @ViewPanel.wraps    
    def Back_to_parent(self):
        if self._current_container.__magicclass_parent__ is None:
            raise ValueError("No more parent!")
        self._current_container = self._current_container.__magicclass_parent__
        self._indent -= 4
    
    @ViewPanel.wraps    
    def Remove_last_widget(self):
        if isinstance(self._current_container, BaseGui) and len(self._current_container) == 0:
            self.Back_to_parent()
        del self._current_container[-1]
        self._code.pop()
        self._create_code()
    
    @ViewPanel.wraps    
    def Reset(self):
        """
        Delete GUI and reset states.
        """        
        self._current_container: None | BaseGui | Container = None
        self._code: list[list[tuple[str, int]]] = []
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
    return ", ".join(f"{k}={Symbol(v)}" for k, v in kwargs.items())