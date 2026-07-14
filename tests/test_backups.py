from __future__ import annotations

import re
import sqlite3

import pytest

from app.database.schema import initialize_database
from app.repositories.settings import SettingsRepository
from app.services.backups import BackupError, BackupService


def _customer_count(db_path) -> int:
    with sqlite3.connect(db_path) as connection:
        return connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]


def _insert_customer(db_path, first_name: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO customers (first_name, last_name, phone, marketing_consent)
            VALUES (?, 'Backup', ?, 0)
            """,
            (first_name, f"099{first_name}"),
        )


def _integrity(path) -> str:
    with sqlite3.connect(path) as connection:
        return connection.execute("PRAGMA integrity_check").fetchone()[0]


def test_manual_backup_creates_timestamped_integral_file_and_logs(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    folder = tmp_path / "backups"
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(folder)}, None, [])
    _insert_customer(db_path, "Manual")

    result = BackupService(db_path).create_manual_backup()

    assert result.path.exists()
    assert re.match(r"club_compras_\d{4}-\d{2}-\d{2}_\d{6}\.db", result.path.name)
    assert _integrity(result.path) == "ok"
    with sqlite3.connect(db_path) as connection:
        backup_action = connection.execute(
            "SELECT action FROM audit_logs WHERE action = 'BACKUP_CREATED'"
        ).fetchone()[0]
        backup_log = connection.execute(
            "SELECT status, reason FROM backup_logs WHERE path = ?",
            (str(result.path),),
        ).fetchone()
    assert backup_action == "BACKUP_CREATED"
    assert backup_log == ("success", "manual")


def test_unavailable_configured_folder_creates_pending_local_backup(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    unavailable_file = tmp_path / "not_a_folder"
    unavailable_file.write_text("ocupado")
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(unavailable_file)}, None, [])

    result = BackupService(db_path).create_manual_backup()

    assert result.status == "pending"
    assert result.path.exists()
    assert result.path.parent.name == "backups"


def test_cleanup_keeps_configured_maximum_and_never_deletes_only_copy(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    folder = tmp_path / "backups"
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(folder)}, None, [])
    service = BackupService(db_path)

    only = service.create_manual_backup().path
    assert service.cleanup_old_backups(keep_count=0) == []
    assert only.exists()

    for index in range(3):
        path = folder / f"club_compras_2026-07-13_20450{index}.db"
        path.write_bytes(only.read_bytes())

    deleted = service.cleanup_old_backups(keep_count=2)

    assert len(deleted) >= 1
    assert len(service.available_backups()) == 2


def test_restore_valid_backup_creates_safety_backup_and_audit(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    folder = tmp_path / "backups"
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(folder)}, None, [])
    service = BackupService(db_path)
    _insert_customer(db_path, "Original")
    backup = service.create_manual_backup()
    _insert_customer(db_path, "Nuevo")

    result = service.restore_backup(backup.path)

    assert _customer_count(db_path) == 1
    assert result.safety_backup_path.exists()
    with sqlite3.connect(db_path) as connection:
        actions = {
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_logs WHERE action IN ('BACKUP_RESTORED', 'BACKUP_CREATED')"
            )
        }
    assert "BACKUP_RESTORED" in actions
    assert "BACKUP_CREATED" in actions


def test_restore_rejects_invalid_file_and_audits_failure(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    invalid = tmp_path / "invalid.db"
    invalid.write_text("no sqlite")
    initialize_database(db_path)
    service = BackupService(db_path)

    with pytest.raises(BackupError):
        service.restore_backup(invalid)

    with sqlite3.connect(db_path) as connection:
        action = connection.execute(
            "SELECT action FROM audit_logs WHERE action = 'BACKUP_RESTORE_FAILED'"
        ).fetchone()[0]
    assert action == "BACKUP_RESTORE_FAILED"
