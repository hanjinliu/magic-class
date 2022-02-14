from magicclass import magicclass, field, set_design
from magicclass.widgets import Separator, LineEdit

@magicclass
class Function:
    """
    This class does almost same thing as FunctionGui.
    You can design GUI easily just by aligning objects
    using field function.
    """
    # The first argument is used to infer widget type
    line = field("text here", name="line_edit")

    # Annotation is also used to determine widget type
    slider = field(name="slider", widget_type="Slider")

    # Or widget class
    sep = Separator()

    @set_design(text="Run")
    def call_button(self):
        s = self.line.value
        i = self.slider.value
        self.result.value = f"{s}-{i}"

    result = LineEdit(enabled=False)

if __name__ == "__main__":
    ui = Function()
    ui.show()
