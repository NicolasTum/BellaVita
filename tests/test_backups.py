from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from app.database.schema import initialize_database
from app.repositories.settings import SettingsRepository
from app.services.backups import BackupError, BackupService, delete_backup_file


def _customer_count(db_path) -> int:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute("SELECT COUNT(*) FROM customers")
        try:
            return cursor.fetchone()[0]
        finally:
            cursor.close()
    finally:
        connection.close()


def _insert_customer(db_path, first_name: str) -> None:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            """
            INSERT INTO customers (first_name, last_name, phone, marketing_consent)
            VALUES (?, 'Backup', ?, 0)
            """,
            (first_name, f"099{first_name}"),
        )
        cursor.close()
        connection.commit()
    finally:
        connection.close()


def _integrity(path) -> str:
    connection = sqlite3.connect(path)
    try:
        cursor = connection.execute("PRAGMA integrity_check")
        try:
            return cursor.fetchone()[0]
        finally:
            cursor.close()
    finally:
        connection.close()


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
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            "SELECT action FROM audit_logs WHERE action = 'BACKUP_CREATED'"
        )
        try:
            backup_action = cursor.fetchone()[0]
        finally:
            cursor.close()
        cursor = connection.execute(
            "SELECT status, reason FROM backup_logs WHERE path = ?",
            (str(result.path),),
        )
        try:
            backup_log = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        connection.close()
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
    assert all(not path.exists() for path in deleted)


def test_manual_backup_can_be_validated_and_deleted_immediately(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    folder = tmp_path / "backups"
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(folder)}, None, [])
    service = BackupService(db_path)

    backup = service.create_manual_backup().path

    assert _integrity(backup) == "ok"
    assert delete_backup_file(backup, retries=1, delay_seconds=0) is True
    assert not backup.exists()


def test_cleanup_deletes_oldest_backups_and_reports_only_deleted_paths(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    folder = tmp_path / "backups"
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(folder)}, None, [])
    service = BackupService(db_path)
    source = service.create_manual_backup().path

    paths = []
    for index in range(4):
        path = folder / f"club_compras_2026-07-13_20451{index}.db"
        path.write_bytes(source.read_bytes())
        paths.append(path)

    deleted = service.cleanup_old_backups(keep_count=2)
    remaining = service.available_backups()

    assert len(remaining) == 2
    assert len(deleted) == 3
    assert all(not path.exists() for path in deleted)
    assert all(path.exists() for path in remaining)
    assert set(deleted).isdisjoint(remaining)
    assert paths[0] in deleted
    assert paths[1] in deleted


def test_delete_backup_file_retries_temporary_lock(tmp_path, monkeypatch) -> None:
    path = tmp_path / "club_compras_2026-07-13_204520.db"
    path.write_text("backup")
    original_unlink = Path.unlink
    attempts = {"count": 0}

    def flaky_unlink(self):
        if self == path and attempts["count"] == 0:
            attempts["count"] += 1
            raise PermissionError("temporarily locked")
        return original_unlink(self)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    assert delete_backup_file(path, retries=3, delay_seconds=0) is True
    assert attempts["count"] == 1
    assert not path.exists()


def test_delete_backup_file_permanent_lock_raises_controlled_error(tmp_path, monkeypatch, caplog) -> None:
    path = tmp_path / "club_compras_2026-07-13_204521.db"
    path.write_text("backup")

    def locked_unlink(self):
        if self == path:
            raise PermissionError("locked")
        raise AssertionError("Unexpected path")

    monkeypatch.setattr(Path, "unlink", locked_unlink)

    with pytest.raises(BackupError):
        delete_backup_file(path, retries=2, delay_seconds=0)

    assert path.exists()
    assert "Could not delete backup" in caplog.text


def test_cleanup_does_not_report_permanently_locked_backup_as_deleted(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "club.db"
    folder = tmp_path / "backups"
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(folder)}, None, [])
    service = BackupService(db_path)
    source = service.create_manual_backup().path
    locked = folder / "club_compras_2026-07-13_204522.db"
    deletable = folder / "club_compras_2026-07-13_204523.db"
    locked.write_bytes(source.read_bytes())
    deletable.write_bytes(source.read_bytes())
    original_unlink = Path.unlink

    def locked_unlink(self):
        if self == locked:
            raise PermissionError("locked")
        return original_unlink(self)

    monkeypatch.setattr(Path, "unlink", locked_unlink)

    deleted = service.cleanup_old_backups(keep_count=1)

    assert locked.exists()
    assert locked not in deleted
    assert all(not path.exists() for path in deleted)
    assert len(service.available_backups()) == 2


def test_cleanup_never_deletes_active_database_even_if_it_matches_backup_pattern(tmp_path) -> None:
    folder = tmp_path / "backups"
    folder.mkdir()
    db_path = folder / "club_compras_2026-07-13_204524.db"
    initialize_database(db_path)
    SettingsRepository(db_path).save_many({"backup_folder_path": str(folder)}, None, [])
    service = BackupService(db_path)

    backup_paths = []
    for index in range(3):
        path = folder / f"club_compras_2026-07-13_204525{index}.db"
        path.write_bytes(db_path.read_bytes())
        backup_paths.append(path)

    deleted = service.cleanup_old_backups(keep_count=1)

    assert db_path.exists()
    assert db_path not in deleted
    assert db_path not in service.available_backups()
    assert len(service.available_backups()) == 1
    assert any(path in deleted for path in backup_paths)


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
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            "SELECT action FROM audit_logs WHERE action IN ('BACKUP_RESTORED', 'BACKUP_CREATED')"
        )
        try:
            actions = {row[0] for row in cursor}
        finally:
            cursor.close()
    finally:
        connection.close()
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

    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.execute(
            "SELECT action FROM audit_logs WHERE action = 'BACKUP_RESTORE_FAILED'"
        )
        try:
            action = cursor.fetchone()[0]
        finally:
            cursor.close()
    finally:
        connection.close()
    assert action == "BACKUP_RESTORE_FAILED"
