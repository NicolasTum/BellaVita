from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config.settings import SETTINGS


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def packaged_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", project_root()))


def resource_path(*parts: str) -> Path:
    return packaged_root().joinpath(*parts)


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / SETTINGS.app_id


def data_dir() -> Path:
    return user_data_dir() / "data"


def database_path() -> Path:
    return data_dir() / "club_compras.db"


def log_dir() -> Path:
    return user_data_dir() / "logs"


def backup_dir() -> Path:
    return user_data_dir() / "backups"


def config_dir() -> Path:
    return user_data_dir() / "config"


def export_dir() -> Path:
    return user_data_dir() / "exports"


def ensure_runtime_dirs() -> None:
    for directory in (data_dir(), log_dir(), backup_dir(), export_dir(), config_dir()):
        directory.mkdir(parents=True, exist_ok=True)
