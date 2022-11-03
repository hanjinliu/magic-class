import pytest
from magicclass import magicclass, magicproperty
from unittest.mock import MagicMock

def test_simple_property():
    mock = MagicMock()

    @magicclass
    class A:
        @magicproperty
        def x(self) -> int:
            mock(action="get", value=self._x)
            return self._x

        @x.setter
        def x(self, v: int):
            mock(action="set", value=v)
            self._x = v

    ui = A()
    mock.assert_not_called()
    ui.x = 10
    mock.assert_called_with(action="set", value=10)
    assert ui.x == 10
    mock.assert_called_with(action="get", value=10)

    spinbox = ui["x"].widget
    btn = ui["x"].call_button

    spinbox.value = 20
    assert ui.x == 10  # not updated yet
    btn.changed()
    assert ui.x == 20  # updated here

def test_annotation_in_getter():
    @magicclass
    class A:
        @magicproperty
        def x(self) -> str:
            return self._x

        @x.setter
        def x(self, v):
            self._x = v

    ui = A()
    assert ui["x"].widget.widget_type == "LineEdit"

def test_annotation_in_setter():
    @magicclass
    class A:
        @magicproperty
        def x(self):
            return self._x

        @x.setter
        def x(self, v: str):
            self._x = v

    ui = A()
    assert ui["x"].widget.widget_type == "LineEdit"

def test_options():
    @magicclass
    class A:
        @magicproperty(options={"choices": ["a", "b", "c"]})
        def x(self):
            return self._x

        @x.setter
        def x(self, v: str):
            self._x = v

    ui = A()
    assert ui["x"].widget.widget_type == "ComboBox"
    ui.x = "b"
    assert ui.x == "b"
    with pytest.raises(ValueError):
        ui.x = "d"
    assert ui.x == "b"


def test_widget_type():
    @magicclass
    class A:
        @magicproperty(widget_type="Slider")
        def x(self):
            return self._x

        @x.setter
        def x(self, v):
            self._x = v

    ui = A()
    assert ui["x"].widget.widget_type == "Slider"

def test_macro():
    @magicclass
    class A:
        @magicproperty
        def x(self) -> int:
            return self._x

        @x.setter
        def x(self, v: int):
            self._x = v

    ui = A()
    assert len(ui.macro) == 1
    ui.x
    assert len(ui.macro) == 1
    ui.x = 5
    assert str(ui.macro[1]) == "ui.x = 5"
    ui.x = 7
    assert str(ui.macro[1]) == "ui.x = 7"

def test_auto_call():

    @magicclass
    class A:
        @magicproperty(auto_call=True)
        def x(self) -> int:
            return self._x

        @x.setter
        def x(self, v: int):
            self._x = v

    ui = A()
    assert len(ui.macro) == 1

    spinbox = ui["x"].widget
    spinbox.value = 10
    assert str(ui.macro[1]) == "ui.x = 10"
