from magicclass import magicclass
from magicclass.widgets import Table, Figure
import os
import pandas as pd
import seaborn as sns
from pathlib import Path

@magicclass(widget_type="tabbed", labels=False)
class TableList:
    """List of table"""

@magicclass(layout="horizontal", widget_type="split")
class Analyzer:
    @magicclass(widget_type="toolbox")
    class Tools:
        @magicclass(widget_type="scrollable")
        class File_Menu:
            def Open_file(self, path: Path): ...
            def Save_file(self, path: Path): ...
            def Save_figure(self, path: Path , transparent: bool): ...
            def Delete_tab(self): ...
            
        @magicclass(widget_type="scrollable")
        class Plot_Menu:
            def Plot(self): ...
            def Histogram(self): ...
            def Box_Plot(self): ...
            def Swarm_Plot(self): ...
            def Violin_Plot(self): ...
            def Boxen_Plot(self): ...
        
        @magicclass(widget_type="scrollable")
        class Plot_Control:
            def set_title(self, title: str): ...
            def set_xlabel(self, label: str): ...
            def set_ylabel(self, label: str): ...
            def set_xlim(self, xmin: str, xmax: str): ...
            def set_ylim(self, ymin: str, ymax: str): ...
            
    table_list = TableList()
    canvas = Figure()
    
    @Tools.File_Menu.wraps
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
        self.table_list.append(table)
        self.table_list.current_index = len(self.table_list) - 1
    
    @Tools.File_Menu.wraps
    def Save_file(self, path: Path):
        """Save current table data as a csv file."""        
        df = self._current_df()
        df.to_csv(path)
    
    @Tools.File_Menu.wraps
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
    
    @Tools.File_Menu.wraps
    def Delete_tab(self):
        """Delete current tab"""        
        try:
            i = self.table_list.current_index
            del self.table_list[i]
        except IndexError:
            pass
    
    @Tools.Plot_Menu.wraps
    def Plot(self):
        """Show plot"""        
        self.canvas.figure.clf()
        df = self._current_df()
        df.plot(ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Menu.wraps
    def Histogram(self):
        """Show histogram"""        
        self.canvas.figure.clf()
        df = self._current_df()
        df.hist(ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Menu.wraps
    def Box_Plot(self):
        """Show box plot"""        
        self._seaborn_plot(sns.boxplot)
    
    @Tools.Plot_Menu.wraps
    def Swarm_Plot(self):
        """Show (bee)swarm plot"""        
        self._seaborn_plot(sns.swarmplot)
    
    @Tools.Plot_Menu.wraps
    def Violin_Plot(self): 
        """Show violin plot"""        
        self._seaborn_plot(sns.violinplot)
    
    @Tools.Plot_Menu.wraps
    def Boxen_Plot(self): 
        """Show boxen plot"""        
        self._seaborn_plot(sns.boxenplot)
    
    @Tools.Plot_Control.wraps
    def set_title(self, title: str):
        """Set title of figure"""        
        self.canvas.ax.set_title(title)
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_xlabel(self, label: str):
        """Set x-label of figure"""        
        self.canvas.ax.set_xlabel(label)
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_ylabel(self, label: str):
        """Set y-label of figure"""        
        self.canvas.ax.set_ylabel(label)
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_xlim(self, xmin: str, xmax: str):
        """Set x-limits of figure"""        
        self.canvas.ax.set_xlim(float(xmin), float(xmax))
        self.canvas.draw()
    
    @Tools.Plot_Control.wraps
    def set_ylim(self, ymin: str, ymax: str):
        """Set y-limits of figure"""        
        self.canvas.ax.set_ylim(float(ymin), float(ymax))
        self.canvas.draw()
        
    def _current_df(self) -> pd.DataFrame:
        i = self.table_list.current_index
        table: Table = self.table_list[i]
        df = table.to_dataframe()
        return df

    def _seaborn_plot(self, plot_function):
        self.canvas.figure.clf()
        df = self._current_df()
        plot_function(data=df, ax=self.canvas.ax)
        self.canvas.draw()
    
if __name__ == "__main__":
    ui = Analyzer()
    ui.show()