from magicclass import magicclass, MagicTemplate
import numpy as np
from scipy import ndimage as ndi
import napari

# A demo of using command registration to run same protocols.
# 1. Open any sample image you want.
# 2. Run "gaussian_filter" -> "normalize" -> "threshold" in order.
# 3. Select the lines in the macro editor and click "Command > Create command".
#    You'll find a new menu action named "Command 0" is appended to the menu.
# 4. Delete all the layer and open another image.
# 5. Click "Command 0". Same functions will be applied to the new image.

@magicclass
class ImageAnalyzer(MagicTemplate):
    def gaussian_filter(self, sigma: float = 1.0):
        layer = self.parent_viewer.layers[-1]
        self.parent_viewer.add_image(
            ndi.gaussian_filter(layer.data, sigma),
            name=layer.name + "-Gaussian"
        )

    def normalize(self):
        layer = self.parent_viewer.layers[-1]
        mn = np.min(layer.data)
        mx = np.max(layer.data)
        self.parent_viewer.add_image(
            (layer.data - mn) / (mx - mn),
            name=layer.name + "-Normalize"
        )

    def threshold(self, thresh: float = 0.5):
        layer = self.parent_viewer.layers[-1]
        self.parent_viewer.add_image(
            layer.data > thresh,
            name=layer.name + "-Threshold"
        )

if __name__ == "__main__":
    ui = ImageAnalyzer()
    viewer = napari.Viewer()
    viewer.window.add_dock_widget(ui)
    ui.macro.widget.show()
    napari.run()
