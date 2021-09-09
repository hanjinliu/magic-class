from magicclass import magicclass, button_design

@magicclass(layout="horizontal")
class Main:
    def __init__(self):
        self.a = 0
        self.b = True
        
    @button_design(text="🔍", font_size=30)
    def search(self, keyword:str): 
        print(magicclass.__doc__.find(keyword))
    
    @button_design(text="🔄", font_size=30)
    def refresh(self): 
        self.a = 0
        self.b = True
    
    @button_design(text="⚙", font_size=30)
    def settings(self, a=0, b=True):
        self.a = a
        self.b = b

m = Main()
m.show()