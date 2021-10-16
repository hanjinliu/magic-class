from magicgui.widgets._bases import widget
from magicclass import magicclass, field, magicmenu
from magicclass.widgets import Table, Figure
import os
import pandas as pd
import seaborn as sns
from pathlib import Path

@magicclass(layout="horizontal", widget_type="split")
class Analyzer:
    @magicclass(widget_type="toolbox")
    class Tools:
        @magicclass(widget_type="scrollable")
        class IO_Menu:
            def Open_file(self, path: Path): ...
            def Save_file(self, path: Path): ...
            def Save_figure(self, path: Path , transparent: bool): ...
            
        @magicclass(widget_type="scrollable")
        class Plot_Menu:
            def Plot(self): ...
            def Scatter_Plot(self): ...
            def Histogram(self): ...
            def Swarm_Plot(self): ...
            def Violin_Plot(self): ...
        
        @magicclass(widget_type="scrollable")
        class Plot_Control:
            def set_xlabel(self, label: str): ...
            def set_ylabel(self, label: str): ...
            def set_xlim(self, xmin: str, xmax: str): ...
            def set_ylim(self, xmin: str, xmax: str): ...
            
    @magicclass(widget_type="tabbed", labels=False)
    class TableList:
        pass
    
    canvas = Figure()
    
    @Tools.IO_Menu.wraps
    def Open_file(self, path: Path, header: str = ""):
        """
        Load data into table.

        Parameters
        ----------
        path : Path
            csv, txt, dat file
        header : str, default is ""
            Where header starts.
        """        
        header = None if header == "" else int(header)
        df = pd.read_csv(path, header=header)
        table = Table(df, name=os.path.basename(path))
        self.TableList.append(table)
        self.TableList.current_index = len(self.TableList) - 1
    
    @Tools.IO_Menu.wraps
    def Save_file(self, path: Path):
        """
        Save current table data as a csv file.
        """        
        df = self._current_df()
        df.to_csv(path)
    
    @Tools.IO_Menu.wraps
    def Save_figure(self, path: Path, transparent=True):
        """
        Save current figure as an image file.

        Parameters
        ----------
        path : Path
            File path.
        transparent : bool, default is True
            Check if you want to save as a transparent image.
        """        
        self.canvas.fig.savefig(path, transparent=transparent)
    
    @Tools.Plot_Menu.wraps
    def Plot(self):
        self.canvas.figure.clf()
        df = self._current_df()
        df.plot(ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Menu.wraps
    def Scatter_Plot(self):
        self.canvas.figure.clf()
        df = self._current_df()
        df.plot.scatter(ax=self.canvas.ax)
        self.canvas.draw()
    
    
    @Tools.Plot_Menu.wraps
    def Histogram(self):
        self.canvas.figure.clf()
        df = self._current_df()
        df.hist(ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Menu.wraps
    def Swarm_Plot(self):
        self.canvas.figure.clf()
        df = self._current_df()
        sns.swarmplot(data=df, ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Menu.wraps
    def Violin_Plot(self): 
        self.canvas.figure.clf()
        df = self._current_df()
        sns.violinplot(data=df, ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_xlabel(self, label: str):
        self.canvas.ax.set_xlabel(label)
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_ylabel(self, label: str):
        self.canvas.ax.set_ylabel(label)
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_xlim(self, xmin: str, xmax: str):
        self.canvas.ax.set_xlim(float(xmin), float(xmax))
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_ylim(self, ymin: str, ymax: str):
        self.canvas.ax.set_ylim(float(ymin), float(ymax))
        self.canvas.draw()
        
    def _current_df(self) -> pd.DataFrame:
        i = self.TableList.current_index
        table: Table = self.TableList[i]
        df = table.to_dataframe()
        return df
    
if __name__ == "__main__":
    ui = Analyzer()
    ui.show()