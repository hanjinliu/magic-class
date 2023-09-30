from __future__ import annotations

from magicgui.widgets import create_widget, Widget, Label
from magicgui.types import Undefined

from magicclass.widgets import TabbedContainer
from magicclass.signature import split_annotated_type, is_annotated


class UnionWidget(TabbedContainer):
    def __init__(
        self,
        annotations: list[type],
        names: list[str] | None = None,
        layout: str = "vertical",
        labels: bool = False,
        nullable: bool = False,
        options: list[dict] | None = None,
        value=Undefined,
        **kwargs,
    ):
        if names is None:
            names: list[str] = []
            for ann in annotations:
                if isinstance(ann, type):
                    names.append(ann.__name__)
                elif is_annotated(ann):
                    _type, _options = split_annotated_type(ann)
                    _name = _options.get("name", _options.get("label", _type.__name__))
                    names.append(_name)

        if options is None:
            options = [{}] * len(annotations)

        widgets: list[Widget] = []
        for ann, name, opt in zip(annotations, names, options):
            _kwargs = dict(name=name, label="")
            _kwargs.update(opt)
            if is_annotated(ann):
                ann, _options = split_annotated_type(ann)
                _kwargs.update(_options)
            wdt = create_widget(annotation=ann, options=_kwargs)
            widgets.append(wdt)

        if nullable:
            widgets.append(Label(value="None", bind=None))

        if "value" in kwargs:
            value = kwargs.pop("value")

        super().__init__(
            layout=layout, widgets=widgets, labels=labels, scrollable=False, **kwargs
        )

        self._annotations = annotations
        if value is not Undefined:
            self.value = value

    @property
    def value(self):
        idx = self.current_index
        return self[idx].value  # type: ignore

    @value.setter
    def value(self, value):
        _type = type(value)
        for idx, ann in enumerate(self._annotations):
            if _type is ann:
                self[idx].value = value  # type: ignore
                self.current_index = idx
                break
        else:
            raise TypeError(f"Cannot set value of type {_type!r}.")
