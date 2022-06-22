from magicgui.widgets import Table
from magicclass import magicclass, field
from magicclass.widgets import SeabornFigure
from magicclass.ext.napari.types import Features, FeatureColumn, FeatureInfo
import napari
import numpy as np

@magicclass
class A:
    def show_feature_as_table(self, features: Features):
        Table(value=features).show()

    def plot_feature_column(self, col: FeatureColumn):
        self.fig.cla()
        self.fig.plot(col)
        self.fig.title(col.name)

    def plot_in_seaborn(self, info: FeatureInfo["x", "y"]):
        df, (x, y) = info
        self.fig.cla()
        self.fig.swarmplot(x=x, y=y, data=df)

    fig = field(SeabornFigure)


if __name__ == "__main__":
    viewer = napari.Viewer()
    ui = A()
    viewer.window.add_dock_widget(ui)
    data0 = np.stack([np.arange(100), 120*np.sin(np.linspace(0, 5, 100))], axis=1)
    data1 = np.stack([np.arange(100), 80*np.cos(np.linspace(0, 5, 100))], axis=1)
    features0 = {
        "Label": np.where(np.random.random(100)>0.3, "X", "Y"),
        "A": np.random.random(100),
        "B": np.random.random(100) * 2,
    }
    features1 = {
        "Label": np.where(np.random.random(100)>0.3, "X", "Y"),
        "column-0": np.random.random(100),
        "column-1": np.random.random(100) + 1,
    }
    viewer.add_points(data0, features=features0)
    viewer.add_points(data1, features=features1)
    napari.run()
