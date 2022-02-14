from magicclass import magicclass, field, build_help
from magicclass.widgets import Table
from enum import Enum
import numpy as np

# "build_help" is very useful for help widget creation.

class Operator(Enum):
    add = "+"
    sub = "-"
    mul = "*"
    div = "/"

@magicclass
class Main:
    @magicclass(widget_type="collapsible")
    class Params:
        """Parameters"""
        a = field(float, options={"tooltip": "Parameter a, which is ..."})
        b = field(float, options={"tooltip": "Parameter b, which is ..."})
        def print_operation(self, op: Operator):
            """
            Print operation such as "1.0 + 3.2" in the console.

            Parameters
            ----------
            op : Operation
                Operator. +, -, * or /.
            """
            print(f"{self.a.value} {op.value} {self.b.value}")

    @magicclass(widget_type="scrollable")
    class TablePanel:
        """
        Table and a button
        """
        table = field(Table, options={"value": np.random.random(size=(4, 3))})
        def print_dataframe(self):
            print(self.table.to_dataframe())

    def show_help(self):
        """
        Using "build_help(ui)", you can make a help widget of "ui".
        """
        build_help(self).show()

if __name__ == "__main__":
    ui = Main()
    ui.show()
