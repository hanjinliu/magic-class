from magicclass import magicclass, inline, button_design
from magicclass.widgets import Separator
from magicgui.widgets import LineEdit, Slider

@magicclass(result_widget=True)
class Function:
    """
    This class does almost same thing as FunctionGui. 
    You can design GUI easily just by aligning objects 
    using inline function.
    """    
    
    line = inline(LineEdit, name="line_edit")
    
    slider = inline(Slider, name="slider")
    
    sep = inline(Separator)
    
    @button_design(text="Run")
    def call_button(self):
        s = self["line_edit"].value
        i = self["slider"].value
        return f"{s}-{i}"

if __name__ == "__main__":
    f = Function()
    f.show()