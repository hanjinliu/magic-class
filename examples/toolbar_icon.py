from magicclass import magicclass, magictoolbar, set_design

@magicclass
class Main:
    @magictoolbar
    class Toolbar:
        # iconfy icons
        @set_design(icon="material-symbols:bomb")
        def bomb(self):
            pass

    @set_design(icon="material-symbols:bomb")
    def bomb(self):
        pass

if __name__ == "__main__":
    ui = Main()
    ui.show(run=True)
