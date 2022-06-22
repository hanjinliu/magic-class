from scipy.ndimage import gaussian_filter
from magicclass import HasFields, vfield
import napari
from napari.layers import Image
from skimage import data

class ImageGaussian(Image, HasFields):
    """
    An custom image layer implemented with Gaussian filter.

    A Subclass of HasFields has `widgets` property that can collect all the MagicField
    and createa a Container widget using `as_container()` method.
    """

    sigma = vfield(0.0, widget_type="FloatSlider", options={"max": 10, "step": 0.1})
    edge = vfield("reflect", options={"choices": ["reflect", "constant", "mirror", "nearest"]})

    @sigma.connect
    @edge.connect
    def _on_parameter_change(self):
        img = gaussian_filter(self._data_original, self.sigma, mode=self.edge)
        self.data = img

    def __init__(self, data, *args, **kwargs):
        self._data_original = data
        super().__init__(data, *args, **kwargs)

if __name__ == "__main__":
    viewer = napari.Viewer()
    img = data.camera()
    layer = ImageGaussian(img)
    viewer.add_layer(layer)
    viewer.window.add_dock_widget(layer.widgets.as_container())

    napari.run()
