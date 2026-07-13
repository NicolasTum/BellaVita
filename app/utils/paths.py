from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config.settings import SETTINGS


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / SETTINGS.app_id


def database_path() -> Path:
    return user_data_dir() / "data" / "club_compras.db"


def log_dir() -> Path:
    return user_data_dir() / "logs"


def backup_dir() -> Path:
    return user_data_dir() / "backups"
