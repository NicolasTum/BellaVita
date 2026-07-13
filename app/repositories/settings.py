from __future__ import annotations

import sqlite3
from pathlib import Path

from app.database.schema import DEFAULT_APP_SETTINGS


class SettingsRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def get_all(self) -> dict[str, str]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute("SELECT key, value FROM app_settings").fetchall()
        values = dict(DEFAULT_APP_SETTINGS)
        values.update({row[0]: row[1] for row in rows})
        return values

    def save_many(
        self,
        values: dict[str, str],
        user_id: int | None,
        audit_actions: list[tuple[str, str, str]],
    ) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute("BEGIN IMMEDIATE")
            previous = {
                row[0]: row[1]
                for row in connection.execute("SELECT key, value FROM app_settings").fetchall()
            }
            for key, value in values.items():
                connection.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (key, value),
                )
            for action, entity, key_prefix in audit_actions:
                old_subset = {key: previous.get(key) for key in values if key.startswith(key_prefix)}
                new_subset = {key: values[key] for key in values if key.startswith(key_prefix)}
                connection.execute(
                    """
                    INSERT INTO audit_logs (user_id, action, entity, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, action, entity, str(old_subset), str(new_subset)),
                )
