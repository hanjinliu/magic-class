from __future__ import annotations
import os
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from pathlib import Path
from qtpy.QtWidgets import QStyle, QApplication
from qtpy.QtGui import QIcon, QImage, QPixmap
from qtpy.QtCore import Qt, QSize

if TYPE_CHECKING:
    from .mgui_ext import PushButtonPlus, AbstractAction


class _IconBase:
    _source: Any

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._source!r})"

    def install(self, dst: PushButtonPlus | AbstractAction) -> None:
        raise NotImplementedError()


class StandardIcon(_IconBase):
    """An object of a standard icon."""

    def __init__(self, source: Any):
        if isinstance(source, str):
            source = getattr(Icon, source)
        self._source = source

    def install(self, dst: PushButtonPlus | AbstractAction) -> None:
        icon = QApplication.style().standardIcon(self._source)
        dst.native.setIcon(icon)


class IconPath(_IconBase):
    """An object of an icon from a path."""

    def __init__(self, source: Any):
        self._source = str(source)

    def __str__(self) -> str:
        return self._source

    def install(self, dst: PushButtonPlus | AbstractAction) -> None:
        icon = QIcon(self._source)
        dst.native.setIcon(icon)
        return None


class ArrayIcon(_IconBase):
    """An object of an icon from numpy array."""

    _source: QImage

    def __init__(self, source: Any):
        import numpy as np

        arr = np.asarray(source)

        from magicgui import _mpl_image

        img = _mpl_image.Image()

        img.set_data(arr)

        val: np.ndarray = img.make_image()
        h, w, _ = val.shape
        self._source = QImage(val, w, h, QImage.Format.Format_RGBA8888)

    def install(self, dst: PushButtonPlus | AbstractAction):
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
        icon = QIcon(qpix)
        dst.native.setIcon(icon)
        return None


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
    elif isinstance(val, str) and hasattr(Icon, val):
        icon = StandardIcon(val)
    else:
        raise TypeError(f"Input {val!r} cannot be converted to an icon.")
    return icon


class Icon(SimpleNamespace):
    """
    Namespace of icons.

    .. code-block:: python

        from magicclass import magicclass, set_design, Icon

        @magicclass
        class A:
            @set_design(icon=Icon.FileIcon)
            def func(self):
                ...

    """

    # fmt: off
    TitleBarMenuButton = QStyle.StandardPixmap.SP_TitleBarMenuButton
    TitleBarMinButton = QStyle.StandardPixmap.SP_TitleBarMinButton
    TitleBarMaxButton = QStyle.StandardPixmap.SP_TitleBarMaxButton
    TitleBarCloseButton = QStyle.StandardPixmap.SP_TitleBarCloseButton
    TitleBarNormalButton = QStyle.StandardPixmap.SP_TitleBarNormalButton
    TitleBarShadeButton = QStyle.StandardPixmap.SP_TitleBarShadeButton
    TitleBarUnshadeButton = QStyle.StandardPixmap.SP_TitleBarUnshadeButton
    TitleBarContextHelpButton = QStyle.StandardPixmap.SP_TitleBarContextHelpButton
    MessageBoxInformation = QStyle.StandardPixmap.SP_MessageBoxInformation
    MessageBoxWarning = QStyle.StandardPixmap.SP_MessageBoxWarning
    MessageBoxCritical = QStyle.StandardPixmap.SP_MessageBoxCritical
    MessageBoxQuestion = QStyle.StandardPixmap.SP_MessageBoxQuestion
    DockWidgetCloseButton = QStyle.StandardPixmap.SP_DockWidgetCloseButton
    DesktopIcon = QStyle.StandardPixmap.SP_DesktopIcon
    TrashIcon = QStyle.StandardPixmap.SP_TrashIcon
    ComputerIcon = QStyle.StandardPixmap.SP_ComputerIcon
    DriveFDIcon = QStyle.StandardPixmap.SP_DriveFDIcon
    DriveHDIcon = QStyle.StandardPixmap.SP_DriveHDIcon
    DriveCDIcon = QStyle.StandardPixmap.SP_DriveCDIcon
    DriveDVDIcon = QStyle.StandardPixmap.SP_DriveDVDIcon
    DriveNetIcon = QStyle.StandardPixmap.SP_DriveNetIcon
    DirOpenIcon = QStyle.StandardPixmap.SP_DirOpenIcon
    DirClosedIcon = QStyle.StandardPixmap.SP_DirClosedIcon
    DirLinkIcon = QStyle.StandardPixmap.SP_DirLinkIcon
    FileIcon = QStyle.StandardPixmap.SP_FileIcon
    FileLinkIcon = QStyle.StandardPixmap.SP_FileLinkIcon
    ToolBarHorizontalExtensionButton = QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton
    ToolBarVerticalExtensionButton = QStyle.StandardPixmap.SP_ToolBarVerticalExtensionButton
    FileDialogStart = QStyle.StandardPixmap.SP_FileDialogStart
    FileDialogEnd = QStyle.StandardPixmap.SP_FileDialogEnd
    FileDialogToParent = QStyle.StandardPixmap.SP_FileDialogToParent
    FileDialogNewFolder = QStyle.StandardPixmap.SP_FileDialogNewFolder
    FileDialogDetailedView = QStyle.StandardPixmap.SP_FileDialogDetailedView
    FileDialogInfoView = QStyle.StandardPixmap.SP_FileDialogInfoView
    FileDialogContentsView = QStyle.StandardPixmap.SP_FileDialogContentsView
    FileDialogListView = QStyle.StandardPixmap.SP_FileDialogListView
    FileDialogBack = QStyle.StandardPixmap.SP_FileDialogBack
    DirIcon = QStyle.StandardPixmap.SP_DirIcon
    DialogOkButton = QStyle.StandardPixmap.SP_DialogOkButton
    DialogCancelButton = QStyle.StandardPixmap.SP_DialogCancelButton
    DialogHelpButton = QStyle.StandardPixmap.SP_DialogHelpButton
    DialogOpenButton = QStyle.StandardPixmap.SP_DialogOpenButton
    DialogSaveButton = QStyle.StandardPixmap.SP_DialogSaveButton
    DialogCloseButton = QStyle.StandardPixmap.SP_DialogCloseButton
    DialogApplyButton = QStyle.StandardPixmap.SP_DialogApplyButton
    DialogResetButton = QStyle.StandardPixmap.SP_DialogResetButton
    DialogDiscardButton = QStyle.StandardPixmap.SP_DialogDiscardButton
    DialogYesButton = QStyle.StandardPixmap.SP_DialogYesButton
    DialogNoButton = QStyle.StandardPixmap.SP_DialogNoButton
    ArrowUp = QStyle.StandardPixmap.SP_ArrowUp
    ArrowDown = QStyle.StandardPixmap.SP_ArrowDown
    ArrowLeft = QStyle.StandardPixmap.SP_ArrowLeft
    ArrowRight = QStyle.StandardPixmap.SP_ArrowRight
    ArrowBack = QStyle.StandardPixmap.SP_ArrowBack
    ArrowForward = QStyle.StandardPixmap.SP_ArrowForward
    DirHomeIcon = QStyle.StandardPixmap.SP_DirHomeIcon
    CommandLink = QStyle.StandardPixmap.SP_CommandLink
    VistaShield = QStyle.StandardPixmap.SP_VistaShield
    BrowserReload = QStyle.StandardPixmap.SP_BrowserReload
    BrowserStop = QStyle.StandardPixmap.SP_BrowserStop
    MediaPlay = QStyle.StandardPixmap.SP_MediaPlay
    MediaStop = QStyle.StandardPixmap.SP_MediaStop
    MediaPause = QStyle.StandardPixmap.SP_MediaPause
    MediaSkipForward = QStyle.StandardPixmap.SP_MediaSkipForward
    MediaSkipBackward = QStyle.StandardPixmap.SP_MediaSkipBackward
    MediaSeekForward = QStyle.StandardPixmap.SP_MediaSeekForward
    MediaSeekBackward = QStyle.StandardPixmap.SP_MediaSeekBackward
    MediaVolume = QStyle.StandardPixmap.SP_MediaVolume
    MediaVolumeMuted = QStyle.StandardPixmap.SP_MediaVolumeMuted
    DirLinkOpenIcon = QStyle.StandardPixmap.SP_DirLinkOpenIcon
    LineEditClearButton = QStyle.StandardPixmap.SP_LineEditClearButton
    DialogYesToAllButton = QStyle.StandardPixmap.SP_DialogYesToAllButton
    DialogNoToAllButton = QStyle.StandardPixmap.SP_DialogNoToAllButton
    DialogSaveAllButton = QStyle.StandardPixmap.SP_DialogSaveAllButton
    DialogAbortButton = QStyle.StandardPixmap.SP_DialogAbortButton
    DialogRetryButton = QStyle.StandardPixmap.SP_DialogRetryButton
    DialogIgnoreButton = QStyle.StandardPixmap.SP_DialogIgnoreButton
    RestoreDefaultsButton = QStyle.StandardPixmap.SP_RestoreDefaultsButton
    CustomBase = QStyle.StandardPixmap.SP_CustomBase
    # fmt: on
