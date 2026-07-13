from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel

from app.utils.paths import resource_path


def logo_path() -> Path:
    return resource_path("assets", "images", "logo_bellavita.png")


def app_icon_path() -> Path:
    if sys.platform == "darwin":
        return resource_path("assets", "icons", "app_icon.icns")
    if sys.platform == "win32":
        return resource_path("assets", "icons", "app_icon.ico")
    return logo_path()


def app_icon() -> QIcon:
    icon = QIcon(str(app_icon_path()))
    if icon.isNull():
        return QIcon(str(logo_path()))
    return icon


def logo_pixmap(max_height: int = 100) -> QPixmap:
    pixmap = QPixmap(str(logo_path()))
    if pixmap.isNull():
        return pixmap
    return pixmap.scaledToHeight(max_height, Qt.SmoothTransformation)


def logo_label(max_height: int = 100) -> QLabel:
    label = QLabel()
    label.setObjectName("BrandLogo")
    label.setAlignment(Qt.AlignCenter)
    pixmap = logo_pixmap(max_height)
    if pixmap.isNull():
        label.setText("BV")
    else:
        label.setPixmap(pixmap)
        label.setFixedSize(pixmap.size())
    return label
