from magicclass import magicclass

@magicclass
class A:
    """
    Class A
    """    
    def func_a0(self):
        print("a0")
    def func_a1(self):
        print("a1")

@magicclass
class B:
    """
    Class B
    """    
    def func_b0(self):
        print("b0")
    def func_b1(self):
        print("b1")    

@magicclass
class Main:
    """
    Main class
    """    
    def __init__(self):
        # Make magic-class instance inside.
        self.a = A()
        self.b = B()
    
    def start_class_A(self):
        self.a.show()
    def start_class_B(self):
        self.b.show()

Main().show()