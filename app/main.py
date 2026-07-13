from __future__ import annotations

import logging
import sys

from app.config.settings import SETTINGS
from app.database.schema import initialize_database
from app.utils.paths import database_path, log_dir


def configure_logging() -> None:
    logs = log_dir()
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=logs / "club_compras.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def run() -> int:
    configure_logging()
    initialize_database(database_path())

    try:
        from PySide6.QtWidgets import QApplication

        from app.ui.main_window import MainWindow
    except ImportError as exc:
        print("PySide6 no esta instalado. Ejecuta: pip install -r requirements.txt")
        logging.exception("PySide6 import failed")
        return 1

    application = QApplication(sys.argv)
    application.setApplicationName(SETTINGS.app_name)
    application.setApplicationVersion(SETTINGS.version)

    window = MainWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(run())
