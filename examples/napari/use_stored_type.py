import napari
import numpy as np
import pandas as pd
from magicclass import magicclass, MagicTemplate
from magicclass.types import Stored
from napari.layers import Image, Labels
from skimage.measure import regionprops_table

@magicclass
class Test(MagicTemplate):
    def random_image(self, shape: tuple[int, int] = (100, 100)) -> Stored[Image]:
        return Image(np.random.random(shape), name="Random")

    def regionprops(
        self, image: Stored[Image], labels: Labels
    ) -> Stored[pd.DataFrame]:
        img = image.data
        lbl = labels.data
        df = regionprops_table(
            lbl, img,
            properties=("intensity_mean", "intensity_max", "intensity_min")
        )
        df = pd.DataFrame(df)
        df.index = range(1, df.index.size + 1)
        return df

    def summarize_features(self, features: Stored[pd.DataFrame]):
        from magicgui.widgets import Table
        table = Table(value=features.describe())
        self.parent_viewer.window.add_dock_widget(table)


if __name__ == "__main__":
    viewer = napari.Viewer()
    ui = Test()
    viewer.window.add_dock_widget(ui)
    ui.macro.widget.show()
