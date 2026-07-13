from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.branding import app_icon, app_icon_path, logo_path, logo_pixmap


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_bellavita_branding_resources_exist() -> None:
    assert logo_path().is_file()
    assert app_icon_path().is_file()


def test_bellavita_branding_loads_in_qt() -> None:
    _app()

    assert not logo_pixmap(100).isNull()
    assert not app_icon().isNull()
