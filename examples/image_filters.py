import napari
from napari.types import ImageData
from magicclass import magicclass
from scipy import ndimage as ndi
from skimage.morphology import disk

@magicclass
class Filters:
    def gaussian_filter(self, img:ImageData, sigma=1.0) -> ImageData:
        """
        Run Gaussian filter
        """
        return ndi.gaussian_filter(img, sigma)

    def median_filter(self, img:ImageData, radius=1.0) -> ImageData:
        """
        Run median filter
        """
        selem = disk(radius)
        return ndi.median_filter(img, footprint=selem)

    def sobel_filter(self, img:ImageData) -> ImageData:
        """
        Run Sobel filter
        """
        return ndi.sobel(img)

    def dog_filter(self, img:ImageData, low_sigma=1.0, high_sigma=1.6) -> ImageData:
        """
        Run Difference of Gaussian filter
        """
        return ndi.gaussian_filter(img, low_sigma) - \
                  ndi.gaussian_filter(img, high_sigma)

if __name__ == "__main__":
    ui = Filters()
    viewer = napari.Viewer()
    viewer.window.add_dock_widget(ui)
    napari.run()
