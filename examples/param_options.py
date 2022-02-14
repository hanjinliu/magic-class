from magicclass import magicclass, set_options

@magicclass
class Main:
    @set_options(x={"widget_type": "FloatSlider",
                    "min": -1,
                    "max": 1,
                    "step": 0.1}
                 )
    def print_float(self, x=0):
        print(x)

    @set_options(c={"widget_type": "RadioButtons",
                    "choices": ["first", "second", "third"],
                    "value": "first"
                    }
                 )
    def choose_one(self, c):
        print(c)

if __name__ == "__main__":
    ui = Main()
    ui.show()
