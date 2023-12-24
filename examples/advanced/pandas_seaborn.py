from magicclass import magicclass, abstractapi, set_design, field
from magicclass.widgets import Table, Figure
import os
import pandas as pd
import seaborn as sns
from pathlib import Path

class CachedTable(Table):
    # Because we have to convert table data into DataFrame many times,
    # DataFrame should be cached.
    def __init__(self, value, **kwargs):
        if isinstance(value, pd.DataFrame):
            self._dataframe = value
        else:
            self._dataframe = None
        super().__init__(value, **kwargs)

    def to_dataframe(self) -> pd.DataFrame:
        if self._dataframe is not None:
            return self._dataframe
        else:
            return super().to_dataframe()

@magicclass(widget_type="tabbed", labels=False)
class TableList:
    """List of tables"""

@magicclass(layout="horizontal", widget_type="split")
class Analyzer:
    @magicclass(widget_type="toolbox")
    class Tools:
        @magicclass(widget_type="scrollable")
        class File_Menu:
            Open_file = abstractapi()
            Save_file = abstractapi()
            Save_figure = abstractapi()
            Delete_tab = abstractapi()

        @magicclass(widget_type="scrollable")
        class Plot_Menu:
            Plot = abstractapi()
            Histogram = abstractapi()
            Box_Plot = abstractapi()
            Swarm_Plot = abstractapi()
            Violin_Plot = abstractapi()
            Boxen_Plot = abstractapi()

        @magicclass(widget_type="scrollable")
        class Plot_Control:
            set_title = abstractapi()
            set_xlabel = abstractapi()
            set_ylabel = abstractapi()
            set_xlim = abstractapi()
            set_ylim = abstractapi()

    table_list = field(TableList)
    canvas = field(Figure)

    @set_design(location=Tools.File_Menu)
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
        table = CachedTable(df, name=os.path.basename(path))
        self.table_list.append(table)
        self.table_list.current_index = len(self.table_list) - 1

    @set_design(location=Tools.File_Menu)
    def Save_file(self, path: Path):
        """Save current table data as a csv file."""
        df = self._current_df()
        df.to_csv(path)

    @set_design(location=Tools.File_Menu)
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

    @set_design(location=Tools.File_Menu)
    def Delete_tab(self):
        """Delete current tab"""
        try:
            i = self.table_list.current_index
            del self.table_list[i]
        except IndexError:
            pass

    @set_design(location=Tools.Plot_Menu)
    def Plot(self):
        """Show plot"""
        self.canvas.figure.clf()
        df = self._current_df()
        df.plot(ax=self.canvas.ax)
        self.canvas.draw()

    @set_design(location=Tools.Plot_Menu)
    def Histogram(self):
        """Show histogram"""
        self.canvas.figure.clf()
        df = self._current_df()
        df.hist(ax=self.canvas.ax)
        self.canvas.draw()

    def _seaborn_plot(self, plot_function, x: str, y: str, hue: str, dodge: bool = False):
        # Seaborn plot functions have the same API.
        # Also, this function can be used as a template of signature with "wraps" method.
        x = x or None
        y = y or None
        hue = hue or None
        self.canvas.figure.clf()
        df = self._current_df()
        plot_function(data=df, ax=self.canvas.ax, x=x, y=y, hue=hue, dodge=dodge)
        self.canvas.draw()

    @set_design(location=Tools.Plot_Menu)
    def Box_Plot(self, x: str, y: str, hue: str, dodge: bool = False):
        """Show box plot"""
        self._seaborn_plot(sns.boxplot, x, y, hue, dodge)

    @set_design(location=Tools.Plot_Menu)
    def Swarm_Plot(self, x: str, y: str, hue: str, dodge: bool = False):
        """Show (bee)swarm plot"""
        self._seaborn_plot(sns.swarmplot, x, y, hue, dodge)

    @set_design(location=Tools.Plot_Menu)
    def Violin_Plot(self, x: str, y: str, hue: str, dodge: bool = False):
        """Show violin plot"""
        self._seaborn_plot(sns.violinplot, x, y, hue, dodge)

    @set_design(location=Tools.Plot_Menu)
    def Boxen_Plot(self, x: str, y: str, hue: str, dodge: bool = False):
        """Show boxen plot"""
        self._seaborn_plot(sns.boxenplot, x, y, hue, dodge)

    @set_design(location=Tools.Plot_Control)
    def set_title(self, title: str):
        """
        Set title of the figure.

        Parameters
        ----------
        title : str
            Figure title.
        """
        self.canvas.ax.set_title(title)
        self.canvas.draw()

    @set_design(location=Tools.Plot_Control)
    def set_xlabel(self, label: str):
        """Set x-label of figure"""
        self.canvas.ax.set_xlabel(label)
        self.canvas.draw()

    @set_design(location=Tools.Plot_Control)
    def set_ylabel(self, label: str):
        """Set y-label of figure"""
        self.canvas.ax.set_ylabel(label)
        self.canvas.draw()

    @set_design(location=Tools.Plot_Control)
    def set_xlim(self, xmin: str, xmax: str):
        """
        Set x-limits of the figure.

        Parameters
        ----------
        xmin : str
            Minimum value.
        xmax : str
            Maximum value.
        """
        self.canvas.ax.set_xlim(float(xmin), float(xmax))
        self.canvas.draw()

    @set_design(location=Tools.Plot_Control)
    def set_ylim(self, ymin: str, ymax: str):
        """
        Set y-limits of the figure.

        Parameters
        ----------
        ymin : str
            Minimum value.
        ymax : str
            Maximum value.
        """
        self.canvas.ax.set_ylim(float(ymin), float(ymax))
        self.canvas.draw()

    def _current_df(self) -> pd.DataFrame:
        i = self.table_list.current_index
        table: Table = self.table_list[i]
        df = table.to_dataframe()
        return df


if __name__ == "__main__":
    ui = Analyzer()
    ui.show(run=True)
