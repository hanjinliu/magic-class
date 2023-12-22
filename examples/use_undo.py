from typing import Annotated
from magicclass import magicclass, field, vfield, MagicTemplate, do_not_record, bind_key
from magicclass.undo import undo_callback

@magicclass(layout="horizontal", labels=False)
class Laser(MagicTemplate):
    bar = vfield(0, widget_type="ProgressBar", record=False).with_options(min=0, max=100)
    percent = vfield(0, widget_type="SpinBox", record=False).with_options(min=0, max=100)

    def apply(self, value: Annotated[int, {"bind": percent}]):
        """Apply laser power."""
        old = self.bar
        self.bar = self.percent = value
        @undo_callback
        def out():
            self.bar = self.percent = old
        return out

@magicclass(layout="horizontal")
class UndoRedo(MagicTemplate):
    @bind_key("Ctrl+Z")
    @do_not_record
    def undo(self):
        self.macro.undo()

    @bind_key("Ctrl+Y")
    @do_not_record
    def redo(self):
        self.macro.redo()

@magicclass(labels=False)
class LaserControl(MagicTemplate):
    laser_blue = field(Laser)
    laser_green = field(Laser)
    laser_red = field(Laser)
    undo_redo = field(UndoRedo)


if __name__ == "__main__":
    ui = LaserControl()
    ui.macro.widget.show()
    ui.show(run=True)
