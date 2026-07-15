from __future__ import annotations

import logging
import re
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.database.schema import initialize_database
from app.repositories.settings import SettingsRepository
from app.utils.paths import backup_dir


LOGGER = logging.getLogger(__name__)
BACKUP_PREFIX = "club_compras_"
BACKUP_SUFFIX = ".db"
BACKUP_NAME_PATTERN = re.compile(r"^club_compras_(\d{4}-\d{2}-\d{2}_\d{6})\.db$")
AUTO_BACKUP_INTERVAL = timedelta(minutes=30)
DEFAULT_KEEP_COUNT = 30


class BackupError(RuntimeError):
    pass


def delete_backup_file(path: Path, retries: int = 3, delay_seconds: float = 0.1) -> bool:
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            path.unlink()
            return True
        except (PermissionError, OSError) as exc:
            LOGGER.warning(
                "Could not delete backup %s on attempt %s/%s: %s",
                path,
                attempt,
                attempts,
                exc,
            )
            if attempt == attempts:
                raise BackupError(f"No se pudo eliminar la copia de seguridad {path}: {exc}") from exc
            time.sleep(delay_seconds)
    return False


def parse_backup_timestamp(path: Path) -> datetime | None:
    match = BACKUP_NAME_PATTERN.fullmatch(path.name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d_%H%M%S")
    except ValueError:
        return None


def backup_sort_key(path: Path) -> tuple[datetime, str]:
    timestamp = parse_backup_timestamp(path)
    if timestamp is None:
        timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    return timestamp, path.name


@dataclass(frozen=True)
class BackupStatus:
    database_path: Path
    configured_backup_dir: Path
    folder_available: bool
    last_success_at: str | None
    available_count: int
    state: str


@dataclass(frozen=True)
class BackupResult:
    path: Path
    status: str
    message: str
    reason: str


@dataclass(frozen=True)
class RestorePreview:
    path: Path
    created_at: datetime
    size_bytes: int


@dataclass(frozen=True)
class RestoreResult:
    restored_from: Path
    safety_backup_path: Path


class BackupService:
    def __init__(self, database_path: Path, settings_repository: SettingsRepository | None = None) -> None:
        self._database_path = database_path
        self._settings_repository = settings_repository or SettingsRepository(database_path)

    def status(self) -> BackupStatus:
        destination = self.backup_folder()
        folder_available = destination.exists() and destination.is_dir()
        last_success = self._last_successful_backup()
        count = len(self.available_backups()) if folder_available else 0
        if not folder_available:
            state = "Carpeta no disponible"
        elif last_success:
            state = "Correcto"
        else:
            state = "Pendiente"
        return BackupStatus(
            database_path=self._database_path,
            configured_backup_dir=destination,
            folder_available=folder_available,
            last_success_at=last_success,
            available_count=count,
            state=state,
        )

    def backup_folder(self) -> Path:
        configured = self._settings_repository.get_all().get("backup_folder_path", "").strip()
        return Path(configured).expanduser() if configured else backup_dir()

    def set_backup_folder(self, folder: Path, user_id: int | None = None) -> None:
        path = folder.expanduser()
        path.mkdir(parents=True, exist_ok=True)
        self._settings_repository.save_many(
            {"backup_folder_path": str(path)},
            user_id,
            [("BACKUP_FOLDER_CHANGED", "app_settings", "backup_")],
        )

    def available_backups(self, folder: Path | None = None) -> list[Path]:
        target = folder or self.backup_folder()
        if not target.exists() or not target.is_dir():
            return []
        active_database = self._database_path.resolve()
        return sorted(
            (
                path
                for path in target.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}")
                if path.is_file() and path.resolve() != active_database
            ),
            key=backup_sort_key,
            reverse=True,
        )

    def create_manual_backup(self, user_id: int | None = None) -> BackupResult:
        return self._create_backup("manual", user_id=user_id, force=True, allow_fallback=True)

    def create_safety_backup(self, user_id: int | None = None) -> BackupResult:
        return self._create_backup("pre_restore", user_id=user_id, force=True, allow_fallback=True)

    def create_automatic_backup(self, reason: str, user_id: int | None = None) -> BackupResult | None:
        if not self._should_create_automatic_backup():
            return None
        return self._create_backup(reason, user_id=user_id, force=False, allow_fallback=True)

    def preview_restore(self, source: Path) -> RestorePreview:
        path = source.expanduser()
        if not path.exists() or not path.is_file():
            raise BackupError("La copia seleccionada no existe.")
        self._assert_integrity(path)
        stat = path.stat()
        return RestorePreview(
            path=path,
            created_at=datetime.fromtimestamp(stat.st_mtime),
            size_bytes=stat.st_size,
        )

    def restore_backup(self, source: Path, user_id: int | None = None) -> RestoreResult:
        path = source.expanduser()
        try:
            self.preview_restore(path)
            safety = self.create_safety_backup(user_id=user_id)
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, self._database_path)
            initialize_database(self._database_path)
            self._assert_integrity(self._database_path)
        except Exception as exc:
            self._record_backup_log(str(path), "error", "No se pudo restaurar la copia.", "restore", str(exc), str(path))
            self._audit(user_id, "BACKUP_RESTORE_FAILED", str(path), str(exc), restored_from=str(path))
            LOGGER.exception("Backup restore failed")
            if isinstance(exc, BackupError):
                raise
            raise BackupError(str(exc)) from exc

        self._record_backup_log(
            str(self._database_path),
            "success",
            "Copia restaurada correctamente.",
            "restore",
            restored_from=str(path),
        )
        self._audit(
            user_id,
            "BACKUP_CREATED",
            str(safety.path),
            "Copia previa creada antes de restaurar.",
        )
        self._audit(
            user_id,
            "BACKUP_RESTORED",
            str(self._database_path),
            "Copia restaurada correctamente.",
            restored_from=str(path),
        )
        return RestoreResult(restored_from=path, safety_backup_path=safety.path)

    def cleanup_old_backups(self, keep_count: int = DEFAULT_KEEP_COUNT, user_id: int | None = None) -> list[Path]:
        backups = sorted(self.available_backups(), key=backup_sort_key)
        if len(backups) <= max(1, keep_count):
            return []
        to_delete = backups[: len(backups) - keep_count]
        if len(backups) - len(to_delete) < 1:
            to_delete = backups[:-1]

        deleted: list[Path] = []
        for path in to_delete:
            try:
                if delete_backup_file(path):
                    deleted.append(path)
            except BackupError as exc:
                LOGGER.warning("Could not delete old backup %s: %s", path, exc)
        if deleted:
            self._record_backup_log(
                str(self.backup_folder()),
                "success",
                f"Se eliminaron {len(deleted)} copias antiguas.",
                "cleanup",
            )
            self._audit(user_id, "BACKUP_CLEANUP", str(self.backup_folder()), f"deleted={len(deleted)}")
        return deleted

    def _create_backup(
        self,
        reason: str,
        user_id: int | None,
        force: bool,
        allow_fallback: bool,
    ) -> BackupResult:
        destination_dir = self.backup_folder()
        fallback_used = False
        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            if not destination_dir.is_dir():
                raise BackupError("La ruta de respaldo no es una carpeta.")
        except Exception as exc:
            if not allow_fallback:
                self._record_failure(destination_dir, reason, exc, user_id)
                raise BackupError("La carpeta de respaldo no está disponible.") from exc
            fallback_used = True
            destination_dir = self._fallback_backup_dir()
            destination_dir.mkdir(parents=True, exist_ok=True)

        backup_path = self._next_backup_path(destination_dir)
        try:
            self._assert_integrity(self._database_path)
            self._sqlite_backup(self._database_path, backup_path)
            self._assert_integrity(backup_path)
            message = "Copia de seguridad creada correctamente."
            status = "pending" if fallback_used else "success"
            if fallback_used:
                message = "Carpeta configurada no disponible; se creó una copia local pendiente."
            self._record_backup_log(str(backup_path), status, message, reason)
            self._audit(user_id, "BACKUP_CREATED", str(backup_path), message)
            self.cleanup_old_backups(DEFAULT_KEEP_COUNT, user_id=user_id)
            return BackupResult(backup_path, status, message, reason)
        except Exception as exc:
            if backup_path.exists():
                try:
                    delete_backup_file(backup_path)
                except BackupError as cleanup_exc:
                    LOGGER.warning("Could not remove failed backup %s: %s", backup_path, cleanup_exc)
            self._record_failure(backup_path, reason, exc, user_id)
            if isinstance(exc, BackupError):
                raise
            raise BackupError(str(exc)) from exc

    def _should_create_automatic_backup(self) -> bool:
        connection = sqlite3.connect(self._database_path)
        try:
            cursor = connection.execute(
                """
                SELECT created_at
                FROM backup_logs
                WHERE status IN ('success', 'pending')
                  AND COALESCE(reason, '') NOT IN ('manual', 'pre_restore', 'restore', 'cleanup')
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            try:
                row = cursor.fetchone()
            finally:
                cursor.close()
            cursor = connection.execute(
                """
                SELECT created_at
                FROM backup_logs
                WHERE status IN ('success', 'pending')
                  AND COALESCE(reason, '') NOT IN ('manual', 'pre_restore', 'restore', 'cleanup')
                  AND date(created_at) = date(CURRENT_TIMESTAMP)
                LIMIT 1
                """
            )
            try:
                today = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        if not row:
            return True
        last = self._parse_sqlite_timestamp(row[0])
        if datetime.now() - last >= AUTO_BACKUP_INTERVAL:
            return True
        return today is None

    def _last_successful_backup(self) -> str | None:
        connection = sqlite3.connect(self._database_path)
        try:
            cursor = connection.execute(
                """
                SELECT created_at
                FROM backup_logs
                WHERE status = 'success' AND COALESCE(reason, '') != 'cleanup'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            try:
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        return row[0] if row else None

    def _record_failure(self, path: Path, reason: str, exc: Exception, user_id: int | None) -> None:
        message = "No se pudo crear la copia de seguridad."
        self._record_backup_log(str(path), "error", message, reason, str(exc))
        self._audit(user_id, "BACKUP_FAILED", str(path), str(exc))
        LOGGER.exception("Backup failed")

    def _record_backup_log(
        self,
        path: str,
        status: str,
        message: str,
        reason: str,
        error: str | None = None,
        restored_from: str | None = None,
    ) -> None:
        connection = sqlite3.connect(self._database_path)
        try:
            cursor = connection.execute(
                """
                INSERT INTO backup_logs (path, status, message, reason, error, restored_from)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (path, status, message, reason, error, restored_from),
            )
            cursor.close()
            connection.commit()
        finally:
            connection.close()

    def _audit(
        self,
        user_id: int | None,
        action: str,
        path: str,
        result: str,
        restored_from: str | None = None,
    ) -> None:
        connection = sqlite3.connect(self._database_path)
        try:
            cursor = connection.execute(
                """
                INSERT INTO audit_logs (user_id, action, entity, new_value, reason)
                VALUES (?, ?, 'backups', ?, ?)
                """,
                (user_id, action, f"path={path};restored_from={restored_from or ''}", result),
            )
            cursor.close()
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _sqlite_backup(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_connection = sqlite3.connect(source)
        destination_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(destination_connection)
            destination_connection.commit()
        finally:
            destination_connection.close()
            source_connection.close()

    @staticmethod
    def _assert_integrity(path: Path) -> None:
        connection = sqlite3.connect(path)
        try:
            cursor = connection.execute("PRAGMA integrity_check")
            try:
                result = cursor.fetchone()[0]
            finally:
                cursor.close()
        finally:
            connection.close()
        if result != "ok":
            raise BackupError(f"Integridad SQLite inválida: {result}")

    def _fallback_backup_dir(self) -> Path:
        preferred = backup_dir()
        try:
            preferred.mkdir(parents=True, exist_ok=True)
            probe = preferred / ".write_test"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
            return preferred
        except OSError:
            return self._database_path.parent / "backups"

    @staticmethod
    def _next_backup_path(destination_dir: Path) -> Path:
        current = datetime.now()
        for _ in range(120):
            candidate = destination_dir / f"{BACKUP_PREFIX}{current.strftime('%Y-%m-%d_%H%M%S')}{BACKUP_SUFFIX}"
            if not candidate.exists():
                return candidate
            current += timedelta(seconds=1)
        raise BackupError("No se pudo generar un nombre único para la copia.")

    @staticmethod
    def _parse_sqlite_timestamp(value: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.fromisoformat(value)
