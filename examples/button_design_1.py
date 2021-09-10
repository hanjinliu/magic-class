from magicclass import magicclass, button_design

color_cycle = ["red", "green", "blue"]

@magicclass
class Main:
    def __init__(self):
        self.i = 0
        
    @button_design(background_color="red", font_family="Consolas")
    def change_color(self):
        self.i = (self.i + 1) % 3
        self["change_color"].background_color = color_cycle[self.i]

if __name__ == "__main__":
    m = Main()
    m.show()