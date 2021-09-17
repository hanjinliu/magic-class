from magicclass import magicclass, click

@magicclass
class Steps:
    """
    Setting buttons to enabled/disabled.
    """    
    @click(enables="step_2", disables="step_1")
    def step_1(self, x=0):
        """
        Prepare a integer
        """        
        self.x = x
    
    @click(enables="step_3", disables="step_2", enabled=False)
    def step_2(self, plus=10):
        """
        Increment
        """        
        self.x += plus
    
    @click(enabled=False)
    def step_3(self):
        """
        Print
        """        
        print(f"Result is {self.x}")

if __name__ == "__main__":
    s = Steps()
    s.show()