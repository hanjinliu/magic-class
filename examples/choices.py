from magicclass import magicclass
from magicclass.types import OneOf

@magicclass
class A:
    def _get_choices(self, w=None) -> list[int]:
        return [1, 2, 3]

    def f(self, x: OneOf["a", "b"]):
        print(x.capitalize())

    def g(self, x: OneOf[_get_choices]):
        print(x.to_bytes())

if __name__ == "__main__":
    ui = A()
    ui.show()
