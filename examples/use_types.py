from magicclass import magicclass
from magicclass.types import Optional

@magicclass
class Main:
    def use_optional(self, x: Optional[int] = None):
        print(x)

if __name__ == "__main__":
    ui = Main()
    ui.show()
