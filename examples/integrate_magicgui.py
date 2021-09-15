from magicgui import magicgui
from magicclass import magicclass

@magicclass(result_widget=True)
class Calculator:
    """
    Simple calculator
    """            
    def __init__(self):
        self.a, self.b = 0, 0
    
    # In this case you should use "field" function, but this is a good
    # example to show how to integrate magicgui into magic-class.
    @magicgui(layout="horizontal", auto_call=True)
    def loader(self, a:float, b:float):
        self.a = a
        self.b = b

    def add(self):
        return self.a + self.b
    
    def subtract(self):
        return self.a - self.b
    
    def multiply(self):
        return self.a * self.b
    
    def divide(self):
        return self.a / self.b

if __name__ == "__main__":
    c = Calculator()
    c.show()