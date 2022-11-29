"""Make magicgui before and after v0.7 compatible."""

from magicgui import __version__ as MAGICGUI_VERSION

if MAGICGUI_VERSION < "0.7.0":
    from magicgui.widgets._bases.value_widget import UNSET as Undefined
    from magicgui.widgets._bases import ValueWidget, ButtonWidget, ContainerWidget
    from magicgui.type_map import _type2callback as type2callback
    from magicgui.widgets._concrete import _LabeledWidget, merge_super_sigs
    from magicgui.widgets._protocols import WidgetProtocol
    from magicgui import _mpl_image

else:
    from magicgui.types import Undefined
    from magicgui.widgets.bases import ValueWidget, ButtonWidget, ContainerWidget
    from magicgui.type_map import type2callback
    from magicgui.widgets._concrete import _LabeledWidget, merge_super_sigs
    from magicgui.widgets.protocols import WidgetProtocol
    from magicgui.widgets._image import _mpl_image
