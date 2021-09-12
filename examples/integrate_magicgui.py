from magicgui import magicgui
from magicgui.widgets import LineEdit
from magicclass import magicclass

@magicclass
class Calculator:
    """
    Simple calculator
    """            
    def __post_init__(self):
        self.a, self.b = 0, 0
        self._result_widget = LineEdit(gui_only=True, name="result")
        self._result_widget.enabled = False
        self.append(self._result_widget)
        
    @magicgui(layout="horizontal", auto_call=True)
    def loader(self, a:float, b:float):
        self.a = a
        self.b = b

    def add(self):
        self._result_widget.value = self.a + self.b
    
    def subtract(self):
        self._result_widget.value = self.a - self.b
    
    def multiply(self):
        self._result_widget.value = self.a * self.b
    
    def divide(self):
        self._result_widget.value = self.a / self.b

if __name__ == "__main__":
    c = Calculator()
    c.show()