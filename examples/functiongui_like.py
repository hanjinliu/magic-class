from magicclass import magicclass, field, button_design
from magicclass.widgets import Separator

@magicclass(result_widget=True)
class Function:
    """
    This class does almost same thing as FunctionGui. 
    You can design GUI easily just by aligning objects 
    using inline function.
    """    
    
    line = field(str, name="line_edit")
    
    slider = field(int, name="slider", widget_type="Slider")
    
    sep = field(Separator)
    
    @button_design(text="Run")
    def call_button(self):
        s = self.line
        i = self.slider
        return f"{s}-{i}"

if __name__ == "__main__":
    f = Function()
    f.show()