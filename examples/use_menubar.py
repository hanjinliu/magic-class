from magicclass import magicclass, magicmenu, set_options
from magicgui.widgets import Image
from pathlib import Path
from skimage import io, filters

@magicclass
class Main:
    @magicmenu
    class File:
        def Open_image(self): ...
        def Save_image(self): ...

    @magicmenu
    class Filters:
        def Gaussian_filter(self, sigma: float = 1): ...
        def Sobel_filter(self): ...

    @File.wraps
    @set_options(path={"filter": "*.png;*.jpeg;*.tif;*.tiff", "mode": "r"})
    def Open_image(self, path: Path):
        """
        Open an image and display.
        """
        self.image.value = io.imread(path)

    @File.wraps
    @set_options(path={"filter": "*.png;*.jpeg;*.tif;*.tiff", "mode": "w"})
    def Save_image(self, path: Path):
        """
        Save current image.
        """
        io.imsave(path, self.image.value)

    @Filters.wraps
    def Gaussian_filter(self, sigma: float = 1):
        """
        Apply Gaussian filter.

        Parameters
        ----------
        sigma : float, default is 1.0
            Standar deviation of Gaussian filter.
        """
        out = filters.gaussian(self.image.value, sigma=sigma)
        self.image.value = out

    @Filters.wraps
    def Sobel_filter(self):
        """
        Apply Sobel filter.
        """
        out = filters.sobel(self.image.value)
        self.image.value = out

    image = Image()

if __name__ == "__main__":
    ui = Main()
    ui.show()
