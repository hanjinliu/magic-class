from ...widgets.utils import FreeWidget


class NapariCanvas(FreeWidget):
    def __init__(self, ndisplay=2, order=(), axis_labels=(), **kwargs):
        import napari

        super().__init__(layout="grid", *kwargs)
        self.viewer = napari.Viewer(
            ndisplay=ndisplay, order=order, axis_labels=axis_labels, show=False
        )

        window = self.viewer.window._qt_viewer.parent().parent()
        self.native.setStyleSheet(window.styleSheet())
        window.setParent(self.native, window.windowFlags())

        # _canvas_overlay is the central QWidget that display layers.
        canvas = self.viewer.window._qt_viewer._canvas_overlay
        canvas.setMinimumHeight(200)
        canvas.setMinimumWidth(200)
        self.set_widget(canvas)

        # dims is the multi-slider widget.
        slider = self.viewer.window._qt_viewer.dims
        self.set_widget(slider)

        # layer control widget should be accessible in GUI, but hidden by default.
        self.layer_controls = FreeWidget(name="layer controls")
        self.layer_controls.set_widget(self.viewer.window._qt_viewer.controls)

        self.layer_controls.native.setParent(
            self.viewer.window._qt_viewer, self.layer_controls.native.windowFlags()
        )

        # layer list widget should be accessible in GUI, but hidden by default.
        self.layer_list = FreeWidget(name="layer list")
        self.layer_list.native.setStyleSheet(window.styleSheet())
        self.layer_list.set_widget(self.viewer.window._qt_viewer.dockLayerList.widget())

        self.layer_list.native.setParent(
            self.viewer.window._qt_viewer, self.layer_list.native.windowFlags()
        )
