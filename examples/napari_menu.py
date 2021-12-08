import napari
from napari.layers import Image, Points
import numpy as np
from magicclass import magicmenu

@magicmenu
class MyMenu:
    def Add_random_points(self, number: int = 40, dimensions: int = 2) -> Points:
        return Points(np.random.random((number, dimensions)) * 100)

    def Add_random_image(self, size_x: int = 128, size_y: int = 128) -> Image:
        return Image(np.random.normal(size=(size_y, size_x)))

    @magicmenu
    class Others:
        def Show_text(self, text: str):
            self.parent_viewer.text_overlay.text = text
        
        def Create_macro(self):
            self.macro.widget.show()


if __name__ == "__main__":
    menu = MyMenu()
    viewer = napari.Viewer()
    viewer.window.main_menu.addMenu(menu.native)
    menu.native.setParent(viewer.window.main_menu, menu.native.windowFlags())
    napari.run()