from __future__ import annotations
import random
import string
import time
from typing import TYPE_CHECKING, Callable
from magicgui.widgets._bases import Widget, ValueWidget
from magicgui.widgets import (
    CheckBox,
    ComboBox,
    Container,
    DateEdit,
    DateTimeEdit,
    FileEdit,
    FloatSlider,
    FloatSpinBox,
    Label,
    LineEdit,
    LogSlider,
    ProgressBar,
    PushButton,
    RadioButton,
    RadioButtons,
    RangeEdit,
    Select,
    SliceEdit,
    Slider,
    SpinBox,
    TextEdit,
    TimeEdit,
)

# WIP!

from .class_gui import ClassGui
from .widgets import FrozenContainer, PushButtonPlus

_CHARS = string.digits + string.ascii_lowercase + string.ascii_uppercase

def _random_choice_int(widget: ValueWidget):
    widget.value = random.randint(widget.min, widget.max)
    widget.changed(value=widget.value)
    return f"{widget.name}.value = {widget.value}"

def _random_choice_float(widget: ValueWidget):
    x0, x1 = widget.min, widget.max
    val = random.random()*(x1-x0)+x0
    widget.value = val
    widget.changed(value=widget.value)
    return f"{widget.name}.value = {widget.value}"

def _random_choice(widget: ValueWidget):
    widget.value = random.choice(widget.choices)
    widget.changed(value=widget.value)
    return f"{widget.name}.value = {widget.value}"

def _random_choices(widget: ValueWidget):
    k = random.randint(0, len(widget.choices))
    widget.value = random.choices(widget.choices, k=k)
    widget.changed(value=widget.value)
    return f"{widget.name}.value = {widget.value}"

def _random_str(widget: ValueWidget):
    k = random.randint(0, 12)
    widget.value = "".join(random.choices(_CHARS, k=k))
    widget.changed(value=widget.value)
    return f"{widget.name}.value = {widget.value}"

def _click(widget: ValueWidget):
    widget.changed()
    return f"{widget.name}.value = {widget.value}"

def _click_and_run(widget: ValueWidget):
    widget.changed()
    if widget.mgui is None:
        return f"{widget.name}()"
    args = []
    for wid in widget.mgui:
        try:
            _TEST_MAP[type(wid)](wid)
        except Exception as e:
            print(e)
        else:
            print("mgui pass")
        if isinstance(wid, PushButton):
            break
        args.append(f"{wid.name}={wid.value}")

    return f"{widget.name}({', '.join(args)})"

def _check(widget: ValueWidget):
    widget.value = not widget.value
    widget.changed(value=widget.value)
    return f"{widget.name}.value = {widget.value}"

_TEST_MAP: dict[type, Callable] = {
    CheckBox: _check,
    ComboBox: _random_choice,
    FloatSlider: _random_choice_float,
    FloatSpinBox: _random_choice_float,
    Label: lambda x: False,
    LineEdit: _random_str,
    LogSlider: _random_choice_float,
    PushButton: _click,
    PushButtonPlus: _click_and_run,
    # RadioButton,
    RadioButtons: _random_choice,
    Select: _random_choices,
    Slider: _random_choice_int,
    SpinBox: _random_choice_int,
    # TextEdit,
}

# TODO: prepare dataset that is difficult to randomly selected

class Tester(Container):
    def __init__(self, gui: ClassGui, niter:int=100, timeout:float=120):
        self.gui = gui
        self.niter = niter
        self.timeout = timeout
        super().__init__(labels=False)
        self.log = TextEdit(name="Tester")
        self.append(self.log)
        self.show()
        self.run()
    
    def run(self):
        total_count = 0
        count = 0
        dprogress = 1/self.niter*1000
        pbar = ProgressBar()
        self.append(pbar)
        t0 = time.time()
        while count < self.niter:
            widget = _choose_widget(self.gui)
            if widget is None:
                pass
            elif not (widget.visible and widget.enabled):
                # Do nothing if widget is inaccessible from UI.
                pass
            else:
                try:
                    x = _TEST_MAP[type(widget)](widget)
                except Exception as e:
                    self.log.native.append([f"{widget.name} Failed", f"{e}"])
                else:
                    if x:
                        self.log.native.append(f"{x}")
                        count += 1
                        pbar.increment(dprogress)
                        
            total_count += 1
            if total_count > max(10000, self.niter):
                pbar.value = 1000
                raise RuntimeError("Iteration exceeded 10000")
            elif time.time() - t0 > self.timeout:
                pbar.value = 1000
                raise RuntimeError("Time out")
        pbar.value = 1000
        return None
                

def _choose_widget(container: Container):
    if isinstance(container, FrozenContainer):
        return None
    widget = random.choice(container)
    if isinstance(widget, Container):
        return _choose_widget(widget)
    else:
        return widget