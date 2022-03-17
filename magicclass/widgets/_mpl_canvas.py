from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backend_bases import MouseEvent, MouseButton
from qtpy import QtWidgets as QtW, QtGui

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes


class InteractiveFigureCanvas(FigureCanvas):
    """A figure canvas implemented with mouse callbacks."""

    figure: Figure

    def __init__(self, fig):
        super().__init__(fig)
        self.pressed = None
        self.lastx_pressed = None
        self.lasty_pressed = None
        self.lastx = None
        self.lasty = None
        self.last_axis: Axes | None = None
        self._interactive = True
        self._mouse_click_callbacks = []

    def wheelEvent(self, event):
        """
        Resize figure by changing axes xlim and ylim. If there are subplots, only the subplot
        in which cursor exists will be resized.
        """
        ax = self.last_axis
        if not self._interactive or not ax:
            return
        delta = event.angleDelta().y() / 120
        event = self.get_mouse_event(event)

        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        xrange = x1 - x0
        yrange = y1 - y0

        if delta > 0:
            factor = 1 / 1.3
        else:
            factor = 1.3

        ax.set_xlim(
            [(x1 + x0) / 2 - xrange / 2 * factor, (x1 + x0) / 2 + xrange / 2 * factor]
        )
        ax.set_ylim(
            [(y1 + y0) / 2 - yrange / 2 * factor, (y1 + y0) / 2 + yrange / 2 * factor]
        )
        self.figure.canvas.draw()
        return None

    def mousePressEvent(self, event):
        """Record the starting coordinates of mouse drag."""

        event = self.get_mouse_event(event)
        self.lastx_pressed = self.lastx = event.xdata
        self.lasty_pressed = self.lasty = event.ydata
        if event.inaxes:
            self.pressed = event.button
            self.last_axis = event.inaxes
        return None

    def mouseMoveEvent(self, event):
        """
        Translate axes focus while dragging. If there are subplots, only the subplot in which
        cursor exists will be translated.
        """
        ax = self.last_axis
        if (
            self.pressed not in (MouseButton.LEFT, MouseButton.RIGHT)
            or self.lastx_pressed is None
            or not self._interactive
            or not ax
        ):
            return

        event = self.get_mouse_event(event)
        x, y = event.xdata, event.ydata

        if x is None or y is None:
            return None

        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        if self.pressed == MouseButton.LEFT:
            distx = x - self.lastx_pressed
            disty = y - self.lasty_pressed
            ax.set_xlim([x0 - distx, x1 - distx])
            ax.set_ylim([y0 - disty, y1 - disty])
        elif self.pressed == MouseButton.RIGHT:
            dx = x - self.lastx
            dy = y - self.lasty
            xrange = x1 - x0
            yrange = y1 - y0
            ax.set_xlim(
                [(x1 + x0) / 2 - xrange / 2 + dx, (x1 + x0) / 2 + xrange / 2 - dx]
            )
            ax.set_ylim(
                [(y1 + y0) / 2 - yrange / 2 + dy, (y1 + y0) / 2 + yrange / 2 - dy]
            )

        self.lastx, self.lasty = x, y
        self.figure.canvas.draw()
        return None

    def mouseReleaseEvent(self, event):
        """Stop dragging state."""
        pos = event.pos()
        event = self.get_mouse_event(event)
        if self.lastx == event.xdata and self.lasty == event.ydata:
            if self.pressed == MouseButton.LEFT:
                for callbacks in self._mouse_click_callbacks:
                    callbacks(event)
            elif self.pressed == MouseButton.RIGHT:
                menu = self._make_context_menu()
                menu.exec_(self.mapToGlobal(pos))
        self.pressed = None
        return None

    def mouseDoubleClickEvent(self, event):
        """Adjust layout upon dougle click."""
        if not self._interactive:
            return
        self.figure.tight_layout()
        self.figure.canvas.draw()
        return None

    def resizeEvent(self, event):
        """Adjust layout upon canvas resized."""
        super().resizeEvent(event)
        self.figure.tight_layout()
        self.figure.canvas.draw()
        return None

    def get_mouse_event(self, event, name="") -> MouseEvent:
        x, y = self.mouseEventCoords(event)
        if hasattr(event, "button"):
            button = self.buttond.get(event.button())
        else:
            button = None
        mouse_event = MouseEvent(name, self, x, y, button=button, guiEvent=event)
        return mouse_event

    def _make_context_menu(self):
        """Make a QMenu object with default actions."""
        menu = QtW.QMenu(self)
        menu.addAction("Copy ...", self._copy_canvas)
        menu.addAction("Save As...", self._save_canvas_dialog)
        menu.addSeparator()
        return menu

    def _save_canvas_dialog(self, format="PNG"):
        """Open a file dialog and save the current canvas state."""
        dialog = QtW.QFileDialog(self, "Save Image")
        dialog.setAcceptMode(QtW.QFileDialog.AcceptSave)
        dialog.setDefaultSuffix(format.lower())
        dialog.setNameFilter(f"{format} file (*.{format.lower()})")
        if dialog.exec_():
            filename = dialog.selectedFiles()[0]
            self._save_canvas(filename)

    def _save_canvas(self, path: str):
        """Save current canvas state at the specified path."""
        self.figure.savefig(path)

    def _asarray(self) -> np.ndarray:
        """Convert current canvas state into RGBA numpy array."""
        return np.asarray(self.renderer.buffer_rgba(), dtype=np.uint8)

    def _copy_canvas(self):
        """Copy current canvas state into clipboard."""
        arr = self._asarray()
        clipboard = QtW.QApplication.clipboard()
        h, w, _ = arr.shape
        image = QtGui.QImage(arr, w, h, QtGui.QImage.Format_RGBA8888)
        clipboard.setImage(image)
