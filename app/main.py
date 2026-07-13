from __future__ import annotations

import logging
import sys

from app.config.settings import SETTINGS
from app.database.bootstrap import ensure_default_admin
from app.database.schema import initialize_database
from app.utils.paths import database_path, log_dir


def configure_logging() -> None:
    logs = log_dir()
    logging_kwargs = {
        "level": logging.INFO,
        "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
    }
    try:
        logs.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=logs / "club_compras.log", **logging_kwargs)
    except OSError:
        logging.basicConfig(stream=sys.stderr, **logging_kwargs)
        logging.exception("Could not initialize file logging")


def run() -> int:
    configure_logging()
    db_path = database_path()
    initialize_database(db_path)
    if ensure_default_admin(db_path):
        logging.info("Default admin user created")

    try:
        from PySide6.QtWidgets import QApplication

        from app.ui.branding import app_icon
        from app.ui.main_window import MainWindow
    except ImportError as exc:
        print("PySide6 no esta instalado. Ejecuta: pip install -r requirements.txt")
        logging.exception("PySide6 import failed")
        return 1

    application = QApplication(sys.argv)
    application.setApplicationName(SETTINGS.app_name)
    application.setApplicationVersion(SETTINGS.version)
    application.setWindowIcon(app_icon())

    window = MainWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(run())
