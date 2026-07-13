from __future__ import annotations

import sqlite3
from pathlib import Path

from app.security.passwords import hash_password


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin123!"


def ensure_default_admin(path: Path) -> bool:
    """Create a first local admin for development and first-run setup.

    Returns True when the user was created. Existing databases are left untouched.
    """
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count > 0:
            return False

        connection.execute(
            """
            INSERT INTO users (
                username,
                display_name,
                password_hash,
                role,
                must_change_password,
                is_active
            )
            VALUES (?, ?, ?, 'admin', 1, 1)
            """,
            (
                DEFAULT_ADMIN_USERNAME,
                "Administrador",
                hash_password(DEFAULT_ADMIN_PASSWORD),
            ),
        )
        connection.execute(
            """
            INSERT INTO audit_logs (action, entity, entity_id, new_value, reason)
            VALUES ('bootstrap_admin_created', 'users', last_insert_rowid(), ?, ?)
            """,
            (
                DEFAULT_ADMIN_USERNAME,
                "Usuario administrador inicial creado automaticamente",
            ),
        )
        return True
