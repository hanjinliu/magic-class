# In magicgui, instead of specifying parameter types, you can use "bind" option to bind
# constant value or a callback function to the parameter. In magicclass you can also
# bind class method or MagicField object. Since the bind option is very useful for
# reproducible macro recording, magicclass also provides helper function "Bound".
# Bound[x] is equivalent to Annotated[X, {"bind": x}]. Type "X" is determined from x.

from magicclass import magicclass, field, set_options
from magicclass.types import Bound
from typing_extensions import Annotated
import numpy as np

@magicclass
class Main:
    mean = field(0.1, widget_type="FloatSlider",
                 options={"max": 1, "step": 0.1}, record=False
                 )
    sd = field(0.1, widget_type="FloatSlider",
               options={"min": 0.01, "max": 0.2, "step": 0.01}, record=False
               )

    def _get_random_value(self, widget):
        # "widget" takes a EmptyWidget object, as is in magicgui
        return np.random.normal(loc=self.mean.value, scale=self.sd.value)

    @set_options(v={"bind": _get_random_value})
    def print_1(self, v):
        print(v)

    def print_2(self, v: Annotated[float, {"bind": _get_random_value}]):
        print(v)

    def print_3(self, v: Bound[_get_random_value]):
        print(v)

    def print_parameters(self, mean: Bound[mean], sd: Bound[sd]):
        print(f"{mean} +/- {sd}")

if __name__ == "__main__":
    ui = Main()
    ui.show()
