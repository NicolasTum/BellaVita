from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.repositories.settings import SettingsRepository


class SettingsPermissionError(PermissionError):
    pass


class SettingsValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CurrentUser:
    id: int | None
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


DEFAULT_ADMIN_USER = CurrentUser(id=None, username="admin", role="admin")


class SettingsService:
    def __init__(self, database_path: Path, current_user: CurrentUser = DEFAULT_ADMIN_USER) -> None:
        self._repository = SettingsRepository(database_path)
        self._current_user = current_user

    def current_user(self) -> CurrentUser:
        return self._current_user

    def can_open_settings(self) -> bool:
        return self._current_user.is_admin

    def require_admin(self) -> None:
        if not self._current_user.is_admin:
            raise SettingsPermissionError("Solo un administrador puede acceder a configuración.")

    def get_settings(self) -> dict[str, str]:
        return self._repository.get_all()

    def loyalty_target_purchase_count(self) -> int:
        settings = self.get_settings()
        return int(settings["loyalty_target_purchase_count"])

    def save_settings(self, values: dict[str, str]) -> None:
        self.require_admin()
        current = self.get_settings()
        merged = dict(current)
        merged.update(values)
        self._validate(merged)

        audit_actions = [("SETTINGS_UPDATED", "app_settings", "")]
        if values.keys() & {
            "loyalty_target_purchase_count",
            "promotion_name",
            "promotion_description",
            "loyalty_active",
            "allow_new_cycle_with_pending_reward",
        }:
            audit_actions.append(("LOYALTY_TARGET_CHANGED", "app_settings", "loyalty_"))
        if any(key.startswith("promotion_sender") or key.startswith("promotion_reply") or key.startswith("promotion_default") or key == "promotion_email_status" for key in values):
            audit_actions.append(("PROMOTION_EMAIL_SETTINGS_UPDATED", "app_settings", "promotion_"))
        if any(key.startswith("store_") or key in {"currency_code", "currency_symbol", "promotion_legal_text", "marketing_consent_required"} for key in values):
            audit_actions.append(("STORE_SETTINGS_UPDATED", "app_settings", "store_"))

        self._repository.save_many(values, self._current_user.id, audit_actions)

    def _validate(self, values: dict[str, str]) -> None:
        try:
            target = int(values["loyalty_target_purchase_count"])
        except ValueError as exc:
            raise SettingsValidationError("La cantidad de compras debe ser un número entero.") from exc
        if not 1 <= target <= 50:
            raise SettingsValidationError("La cantidad de compras debe estar entre 1 y 50.")
        if not values.get("store_name", "").strip():
            raise SettingsValidationError("El nombre de la tienda es obligatorio.")
        if not values.get("currency_symbol", "").strip():
            raise SettingsValidationError("El símbolo monetario es obligatorio.")
        for key in ("promotion_sender_email", "promotion_reply_to_email", "store_email"):
            email = values.get(key, "").strip()
            if email and "@" not in email:
                raise SettingsValidationError("Revisá el formato de los correos.")
