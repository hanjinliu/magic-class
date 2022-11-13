from __future__ import annotations

from typing import Iterable, Callable, TYPE_CHECKING
from magicgui import register_type, application as app
from magicgui.widgets import Container, ComboBox, Label, Widget

from napari.utils._magicgui import find_viewer_ancestor

if TYPE_CHECKING:
    from .types import Features, FeatureColumn


def get_features(widget: Widget) -> list[tuple[str, Features]]:
    """Get all the non-empty feature data from the viewer."""
    viewer = find_viewer_ancestor(widget)
    if viewer is None:
        return []
    features: list[Features] = []
    for layer in viewer.layers:
        if len(feat := getattr(layer, "features", [])) > 0:
            features.append((layer.name, feat))
    return features


# Widget
class ColumnChoice(Container):
    def __init__(
        self,
        data_choices: Iterable[Features] | Callable[[Widget], Iterable[Features]],
        value=None,
        **kwargs,
    ):
        self._dataframe_cbox = ComboBox(choices=data_choices, value=value, **kwargs)
        self._column_cbox = ComboBox(choices=self._get_available_columns)
        _measure = app.use_app().get_obj("get_text_width")
        _label_l = Label(value='.features["')
        _label_l.max_width = _measure(_label_l.value)
        _label_r = Label(value='"]')
        _label_r.max_width = _measure(_label_r.value)

        super().__init__(
            layout="horizontal",
            widgets=[self._dataframe_cbox, _label_l, self._column_cbox, _label_r],
            labels=False,
            name=kwargs.get("name"),
        )
        self.margins = (0, 0, 0, 0)
        self._dataframe_cbox.changed.connect(self._set_available_columns)

    def _get_available_columns(self, w=None):
        df: Features = self._dataframe_cbox.value
        cols = getattr(df, "columns", [])
        return cols

    def _set_available_columns(self, w=None):
        cols = self._get_available_columns()
        self._column_cbox.choices = cols
        return None

    @property
    def value(self) -> FeatureColumn:
        df = self._dataframe_cbox.value
        return df[self._column_cbox.value]


class ColumnNameChoice(Container):
    """
    A container widget with a DataFrame selection and multiple column name selections.

    This widget is composed of two or more ComboBox widgets. The top one is to choose a
    DataFrame and the rest are to choose column names from the DataFrame. When the DataFrame
    selection changed, the column name selections will also changed accordingly.
    """

    def __init__(
        self,
        data_choices: Iterable[Features] | Callable[[Widget], Iterable[Features]],
        column_choice_names: Iterable[str],
        value=None,
        **kwargs,
    ):
        self._dataframe_cbox = ComboBox(choices=data_choices, value=value, **kwargs)
        self._column_names_cbox: list[ComboBox] = []
        for cn in column_choice_names:
            self._column_names_cbox.append(
                ComboBox(choices=self._get_available_columns, name=cn, nullable=True)
            )
        self._child_container = Container(
            widgets=self._column_names_cbox, layout="vertical"
        )
        self._child_container.margins = (0, 0, 0, 0)
        super().__init__(
            layout="vertical",
            widgets=[self._dataframe_cbox, self._child_container],
            labels=False,
            name=kwargs.get("name"),
        )
        self.margins = (0, 0, 0, 0)
        self._dataframe_cbox.changed.connect(self._set_available_columns)

    def _get_available_columns(self, w=None):
        df: Features = self._dataframe_cbox.value
        cols = getattr(df, "columns", [])
        return cols

    def _set_available_columns(self, w=None):
        cols = self._get_available_columns()
        for cbox in self._column_names_cbox:
            cbox.choices = cols
        return None

    @property
    def value(self) -> tuple[Features, list[str]]:
        df = self._dataframe_cbox.value
        colnames = [cbox.value for cbox in self._column_names_cbox]
        return (df, colnames)


def _register_mgui_types():
    from .types import Features, FeatureColumn, FeatureInfoInstance

    register_type(Features, choices=get_features, nullable=False)

    register_type(
        FeatureColumn,
        widget_type=ColumnChoice,
        data_choices=get_features,
        nullable=False,
    )

    register_type(
        FeatureInfoInstance,
        widget_type=ColumnNameChoice,
        data_choices=get_features,
    )
