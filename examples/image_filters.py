import napari
from napari.types import ImageData
from magicclass import magicclass
from scipy import ndimage as ndi
from skimage.morphology import disk
from functools import wraps

def record_macro(func):
    @wraps(func)
    def wrapped(self, img, *args, **kwargs):
        out = func(self, img, *args, **kwargs)
        sym = self._get_symbol(img)
        symout = self._get_symbol(out)
        args = ",".join(map(str, args))
        self._macro.append(f"{symout} = filt.{func.__name__}({sym}, {args})")
        return out
    return wrapped

@magicclass
class Filters:
    def __init__(self):
        self._macro = []
        self.images = {}

    @property
    def macro(self):
        return "\n".join(self._macro)

    def _get_symbol(self, img):
        id_ = id(img)
        if id_ not in self.images:
            self.images[id_] = f"img{len(self.images)}"
        return self.images[id_]

    @record_macro
    def gaussian_filter(self, img:ImageData, sigma=1.0) -> ImageData:
        """
        Run Gaussian filter
        """
        return ndi.gaussian_filter(img, sigma)

    @record_macro
    def median_filter(self, img:ImageData, radius=1.0) -> ImageData:
        """
        Run median filter
        """
        selem = disk(radius)
        return ndi.median_filter(img, footprint=selem)

    @record_macro
    def sobel_filter(self, img:ImageData) -> ImageData:
        """
        Run Sobel filter
        """
        return ndi.sobel(img)

    @record_macro
    def dog_filter(self, img:ImageData, low_sigma=1.0, high_sigma=1.6) -> ImageData:
        """
        Run Difference of Gaussian filter
        """
        return ndi.gaussian_filter(img, low_sigma) - \
                  ndi.gaussian_filter(img, high_sigma)

if __name__ == "__main__":
    filt = Filters()
    viewer = napari.Viewer()
    viewer.window.add_dock_widget(filt)
    napari.run()