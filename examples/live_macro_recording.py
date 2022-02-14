from magicclass import magicclass, magicgui, field, vfield
from datetime import datetime, date, time

# In this example, you'll see macro is updated in real time when you changed any values.

@magicclass
class Main:
    a = field(int)
    b = field(str)

    @magicgui(auto_call=True, layout="horizontal")
    def func(self, u: date, v: time):
        print(u, v)

    w = vfield(datetime)

    def __post_init__(self):
        # To keep macro docked, append macro widget to main widget here
        self.append(self.macro.widget)

if __name__ == "__main__":
    ui = Main()
    ui.show()
