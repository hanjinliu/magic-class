from magicclass import magicclass
from magicclass.types import Optional, Union

@magicclass
class Main:
    def use_optional(self, x: Optional[int] = None):
        print(x)

    def use_union(self, x: Union[int, str] = 0):
        print(x)

if __name__ == "__main__":
    ui = Main()
    ui.show(run=True)
