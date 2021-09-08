from magicclass import magicclass, click

@magicclass
class Steps:
    @click(enables="step_2", disables="step_1")
    def step_1(self, x=0):
        self.x = x
    
    @click(enables="step_3", disables="step_2", enabled=False)
    def step_2(self, plus=10):
        self.x += plus
    
    @click(enabled=False)
    def step_3(self):
        print(f"Result is {self.x}")

Steps().show()