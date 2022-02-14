from magicgui import magicgui
from magicclass import magicclass, field

@magicclass
class Calculator:
    """
    Simple calculator
    """
    def __init__(self):
        self.a, self.b = 0, 0

    # In this case you should use "field" function, but this is a good
    # example to show how to integrate magicgui into magic-class.
    @magicgui(layout="horizontal", auto_call=True)
    def loader(self, a: float, b: float):
        self.a = a
        self.b = b

    def add(self):
        self.answer.value =  self.a + self.b

    def subtract(self):
        self.answer.value =  self.a - self.b

    def multiply(self):
        self.answer.value =  self.a * self.b

    def divide(self):
        self.answer.value =  self.a / self.b

    answer = field(str, options={"enabled": False})

if __name__ == "__main__":
    ui = Calculator()
    ui.show()
