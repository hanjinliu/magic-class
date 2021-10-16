from magicclass import magicclass, field, magicmenu
from magicclass.widgets import Table, Figure
import os
import pandas as pd
import seaborn as sns
from pathlib import Path

@magicclass(layout="horizontal")
class Analyzer:
    @magicclass(widget_type="toolbox")
    class Tools:
        @magicclass(widget_type="scrollable")
        class IO_Menu:
            def Open_file(self, path: Path): ...
            def Save_file(self, path: Path): ...
            
        @magicclass(widget_type="scrollable")
        class Plot_Menu:
            def Plot(self): ...
            def Swarm_Plot(self): ...
            def Violin_Plot(self): ...
        
        @magicclass(widget_type="scrollable")
        class Plot_Control:
            legend = field(True)
            
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
    
    @Tools.Plot_Menu.wraps
    def Plot(self):
        self.canvas.ax.cla()
        i = self.TableList.current_index
        table: Table = self.TableList[i]
        df = table.to_dataframe()
        df.plot(ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Menu.wraps
    def Swarm_Plot(self):
        self.canvas.ax.cla()
        i = self.TableList.current_index
        table: Table = self.TableList[i]
        df = table.to_dataframe()
        sns.swarmplot(data=df, ax=self.canvas.ax)
        self.canvas.draw()
    
    @Tools.Plot_Menu.wraps
    def Violin_Plot(self): ...
    
    @Tools.Plot_Control.legend.connect
    def _legend(self, e):
        value = self.Tools.Plot_Control.legend.value
        self.canvas.ax.legend(value)

if __name__ == "__main__":
    ui = Analyzer()
    ui.show()