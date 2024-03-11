from typing import Annotated
from magicclass import magicclass

@magicclass
class A:
    def _get_choices(self, w=None) -> list[int]:
        return [1, 2, 3]

    # Use the "choices" key to specify the available values.
    def f(self, x: Annotated[str, {"choices": ["a", "b"]}]):
        print(x.capitalize())

    # A choice provider function is also supported.
    def g(self, x: Annotated[int, {"choices": _get_choices}]):
        print(x.to_bytes())

if __name__ == "__main__":
    ui = A()
    ui.show(run=True)
