from magicclass import magicclass, inline

# 1. Keep other magic-class as instances.
@magicclass(layout="horizontal")
class A:
    """
    Class A
    """    
    def func_a0(self):
        print("a0")
    def func_a1(self):
        print("a1")

@magicclass(layout="horizontal")
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
    
# 2. Inline definition
@magicclass
class Main2:
    """
    Main class II
    inline definition
    """    
    @magicclass(layout="horizontal")
    class A2:
        """
        Class A
        """    
        def func_a0(self):
            print("a0")
        def func_a1(self):
            print("a1")

    @magicclass(layout="horizontal")
    class B2:
        """
        Class B
        """    
        def func_b0(self):
            print("b0")
        def func_b1(self):
            print("b1")    

# inline definition using inline function
@magicclass(layout="horizontal")
class A3:
    """
    Class A
    """    
    def func_a0(self):
        print("a0")
    def func_a1(self):
        print("a1")

@magicclass(layout="horizontal")
class B3:
    """
    Class B
    """    
    def func_b0(self):
        print("b0")
    def func_b1(self):
        print("b1")    
        
@magicclass
class Main3:
    """
    Main class III
    inline definition using inline function
    """    
    A = inline(A3)
    B = inline(B3)
    
if __name__ == "__main__":
    m = Main()
    m.show()
    m = Main2()
    m.show()
    m = Main3()
    m.show()
    