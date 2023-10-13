from __future__ import annotations
import os
import warnings
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from pathlib import Path
from qtpy.QtWidgets import QStyle, QApplication, QWidget, QAction
from qtpy.QtGui import QIcon, QImage, QPixmap, QPalette
from qtpy.QtCore import Qt, QSize

import superqt

if TYPE_CHECKING:
    from .mgui_ext import PushButtonPlus, AbstractAction
    from magicgui.widgets import Widget


class _IconBase:
    _source: Any

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._source!r})"

    def get_qicon(self, dst: Widget | AbstractAction) -> QIcon:
        raise NotImplementedError()

    def install(self, dst: PushButtonPlus | AbstractAction) -> None:
        icon = self.get_qicon(dst)
        dst.native.setIcon(icon)


class StandardIcon(_IconBase):
    """An object of a standard icon."""

    def __init__(self, source: Any):
        if isinstance(source, str):
            source = getattr(Icon, source)
        self._source = source

    def get_qicon(self, dst) -> QIcon:
        return QApplication.style().standardIcon(self._source)


class IconPath(_IconBase):
    """An object of an icon from a path."""

    def __init__(self, source: Any):
        self._source = str(source)

    def __str__(self) -> str:
        return self._source

    def get_qicon(self, dst) -> QIcon:
        return QIcon(self._source)


class ArrayIcon(_IconBase):
    """An object of an icon from numpy array."""

    _source: QImage

    def __init__(self, source: Any):
        import numpy as np
        from magicgui.widgets._image import _mpl_image

        arr = np.asarray(source)
        img = _mpl_image.Image()
        img.set_data(arr)

        val: np.ndarray = img.make_image()
        h, w, _ = val.shape
        self._source = QImage(val, w, h, QImage.Format.Format_RGBA8888)

    def get_qicon(self, dst) -> QIcon:
        if hasattr(dst.native, "size"):
            qsize = dst.native.size()
        else:
            qsize = QSize(32, 32)
        qimg = self._source.scaled(
            qsize,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        qpix = QPixmap.fromImage(qimg)
        return QIcon(qpix)


class IconifyIcon(_IconBase):
    _source: str

    def __init__(self, source: Any):
        if ":" not in source:
            # for parity with the other backends, assume fontawesome
            # if no prefix is given.
            source = f"fa:{source}"

        self._source = source

    def get_qicon(self, dst) -> QIcon:
        if isinstance(dst.native, QWidget):
            palette = dst.native.palette()
        elif isinstance(dst.native, QAction):
            if menu := dst.native.parentWidget():
                palette = menu.palette()
            else:
                palette = None
        else:
            return QIcon()

        if palette is None:
            color = "#333333"
        else:
            # use foreground color
            color = palette.color(QPalette.ColorRole.WindowText).name()
            # don't use full black or white
            color = {"#000000": "#333333", "#ffffff": "#cccccc"}.get(color, color)
        try:
            return superqt.QIconifyIcon(self._source, color=color)
        except (OSError, ValueError) as e:
            warnings.warn(f"Could not set iconify icon: {e}", stacklevel=2)
            return QIcon()


def get_icon(val: Any) -> _IconBase:
    """Get a proper icon object from a value."""
    if isinstance(val, _IconBase):
        icon = val
    elif isinstance(val, int):
        icon = StandardIcon(val)
    elif isinstance(val, Path) or os.path.exists(val):
        icon = IconPath(val)
    elif hasattr(val, "__array__"):
        icon = ArrayIcon(val)
    elif isinstance(val, str):
        if hasattr(Icon, val):
            icon = StandardIcon(val)
        else:
            icon = IconifyIcon(val)
    else:
        raise TypeError(f"Input {val!r} cannot be converted to an icon.")
    return icon


class _StandardPixmap:
    """To avoid version dependency."""

    def __getattr__(self, name):
        return getattr(QStyle.StandardPixmap, name, None)


sp = _StandardPixmap()


class Icon(SimpleNamespace):
    """
    Namespace of icons.

    .. code-block:: python

    >>> from magicclass import magicclass, set_design, Icon

    >>> @magicclass
    >>> class A:
    ...     @set_design(icon=Icon.FileIcon)
    ...     def func(self):
    ...         ...

    """

    # fmt: off
    TitleBarMenuButton = sp.SP_TitleBarMenuButton
    TitleBarMinButton = sp.SP_TitleBarMinButton
    TitleBarMaxButton = sp.SP_TitleBarMaxButton
    TitleBarCloseButton = sp.SP_TitleBarCloseButton
    TitleBarNormalButton = sp.SP_TitleBarNormalButton
    TitleBarShadeButton = sp.SP_TitleBarShadeButton
    TitleBarUnshadeButton = sp.SP_TitleBarUnshadeButton
    TitleBarContextHelpButton = sp.SP_TitleBarContextHelpButton
    MessageBoxInformation = sp.SP_MessageBoxInformation
    MessageBoxWarning = sp.SP_MessageBoxWarning
    MessageBoxCritical = sp.SP_MessageBoxCritical
    MessageBoxQuestion = sp.SP_MessageBoxQuestion
    DockWidgetCloseButton = sp.SP_DockWidgetCloseButton
    DesktopIcon = sp.SP_DesktopIcon
    TrashIcon = sp.SP_TrashIcon
    ComputerIcon = sp.SP_ComputerIcon
    DriveFDIcon = sp.SP_DriveFDIcon
    DriveHDIcon = sp.SP_DriveHDIcon
    DriveCDIcon = sp.SP_DriveCDIcon
    DriveDVDIcon = sp.SP_DriveDVDIcon
    DriveNetIcon = sp.SP_DriveNetIcon
    DirOpenIcon = sp.SP_DirOpenIcon
    DirClosedIcon = sp.SP_DirClosedIcon
    DirLinkIcon = sp.SP_DirLinkIcon
    FileIcon = sp.SP_FileIcon
    FileLinkIcon = sp.SP_FileLinkIcon
    ToolBarHorizontalExtensionButton = sp.SP_ToolBarHorizontalExtensionButton
    ToolBarVerticalExtensionButton = sp.SP_ToolBarVerticalExtensionButton
    FileDialogStart = sp.SP_FileDialogStart
    FileDialogEnd = sp.SP_FileDialogEnd
    FileDialogToParent = sp.SP_FileDialogToParent
    FileDialogNewFolder = sp.SP_FileDialogNewFolder
    FileDialogDetailedView = sp.SP_FileDialogDetailedView
    FileDialogInfoView = sp.SP_FileDialogInfoView
    FileDialogContentsView = sp.SP_FileDialogContentsView
    FileDialogListView = sp.SP_FileDialogListView
    FileDialogBack = sp.SP_FileDialogBack
    DirIcon = sp.SP_DirIcon
    DialogOkButton = sp.SP_DialogOkButton
    DialogCancelButton = sp.SP_DialogCancelButton
    DialogHelpButton = sp.SP_DialogHelpButton
    DialogOpenButton = sp.SP_DialogOpenButton
    DialogSaveButton = sp.SP_DialogSaveButton
    DialogCloseButton = sp.SP_DialogCloseButton
    DialogApplyButton = sp.SP_DialogApplyButton
    DialogResetButton = sp.SP_DialogResetButton
    DialogDiscardButton = sp.SP_DialogDiscardButton
    DialogYesButton = sp.SP_DialogYesButton
    DialogNoButton = sp.SP_DialogNoButton
    ArrowUp = sp.SP_ArrowUp
    ArrowDown = sp.SP_ArrowDown
    ArrowLeft = sp.SP_ArrowLeft
    ArrowRight = sp.SP_ArrowRight
    ArrowBack = sp.SP_ArrowBack
    ArrowForward = sp.SP_ArrowForward
    DirHomeIcon = sp.SP_DirHomeIcon
    CommandLink = sp.SP_CommandLink
    VistaShield = sp.SP_VistaShield
    BrowserReload = sp.SP_BrowserReload
    BrowserStop = sp.SP_BrowserStop
    MediaPlay = sp.SP_MediaPlay
    MediaStop = sp.SP_MediaStop
    MediaPause = sp.SP_MediaPause
    MediaSkipForward = sp.SP_MediaSkipForward
    MediaSkipBackward = sp.SP_MediaSkipBackward
    MediaSeekForward = sp.SP_MediaSeekForward
    MediaSeekBackward = sp.SP_MediaSeekBackward
    MediaVolume = sp.SP_MediaVolume
    MediaVolumeMuted = sp.SP_MediaVolumeMuted
    DirLinkOpenIcon = sp.SP_DirLinkOpenIcon
    LineEditClearButton = sp.SP_LineEditClearButton
    DialogYesToAllButton = sp.SP_DialogYesToAllButton
    DialogNoToAllButton = sp.SP_DialogNoToAllButton
    DialogSaveAllButton = sp.SP_DialogSaveAllButton
    DialogAbortButton = sp.SP_DialogAbortButton
    DialogRetryButton = sp.SP_DialogRetryButton
    DialogIgnoreButton = sp.SP_DialogIgnoreButton
    RestoreDefaultsButton = sp.SP_RestoreDefaultsButton
    CustomBase = sp.SP_CustomBase
    # fmt: on
