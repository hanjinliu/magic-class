from magicgui import magicgui
from magicclass import magicclass
import pandas as pd
from pathlib import Path

@magicclass
class C:
    @magicgui
    def loader(self, path:Path, sep:str=","):
        self.path = path
        self.df = pd.read_csv(path, sep=sep)

    def show_path(self):
        print(self.path)

    def show_data(self):
        print(self.df)

if __name__ == "__main__":
    c = C()
    c.show()