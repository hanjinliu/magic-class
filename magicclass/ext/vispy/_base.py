from vispy.visuals import Visual


class LayerItem:
    _visual: Visual

    @property
    def visible(self) -> bool:
        return self._visual.visible

    @visible.setter
    def visible(self, v: bool) -> None:
        self._visual.visible = v
