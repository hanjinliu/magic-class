from magicclass import magicclass
from magicclass.types import List, Tuple, Optional

@magicclass
class Main:
    def use_list(self, l: List[int] = (1,)):
        print(l)

    def use_tuple(self, t: Tuple[int, str]):
        print(t)

    def use_optional(self, x: Optional[int] = None):
        print(x)

if __name__ == "__main__":
    ui = Main()
    ui.show()
