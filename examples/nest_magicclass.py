from magicclass import magicclass

# Magic-class can be nested. There are several ways of nesting magic-classes.

# 2. Inline definition
@magicclass
class Main1:
    """
    Main class I
    inline definition
    """
    @magicclass(layout="horizontal")
    class A1:
        """
        Class A
        """
        def func_a0(self):
            print("a0")
        def func_a1(self):
            print("a1")

    @magicclass(layout="horizontal")
    class B1:
        """
        Class B
        """
        def func_b0(self):
            print("b0")
        def func_b1(self):
            print("b1")

# inline definition using field function
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

@magicclass
class Main2:
    """
    Main class II
    """
    A = A2()
    B = B2()

if __name__ == "__main__":
    m1 = Main1()
    m1.show()
    m2 = Main2()
    m2.show()
