from magicclass import magicclass, magicmenu, bind_key, field

@magicclass
class A:
    @magicmenu
    class Menu:
        @bind_key("Ctrl+T")
        def print_0(self):
            print(0)

        @bind_key("Ctrl+K, Ctrl+T")
        def print_1(self):
            print(1)

        @bind_key("Ctrl", "A")
        def a(self):...

    label_text = field(
        "Ctrl+T to print 0\n"
        "Ctrl+K, Ctrl+T to print 1",
        widget_type="Label",
    )

if __name__ == "__main__":
    ui = A()
    ui.show(run=True)
