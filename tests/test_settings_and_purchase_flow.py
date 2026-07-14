from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sqlite3

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.database.schema import initialize_database
from app.services.customers import CustomerService
from app.services.purchases import PurchaseService
from app.services.rewards import RewardService
from app.services.settings import CurrentUser, SettingsPermissionError, SettingsService, SettingsValidationError
from app.ui.main_window import MainWindow
from app.ui.purchase_page import PurchasePage
from app.ui.settings_page import SettingsPage
from app.version import VERSION


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _customer(db_path, phone: str = "099777000") -> int:
    service = CustomerService(db_path)
    return service.create_customer(
        service.build_customer("Config", "Cliente", phone, "", "", False)
    ).customer_id


def _simple(service: PurchaseService, customer_id: int, index: int):
    return service.register_purchase(
        service.build_simple_purchase(
            customer_id,
            f"Compra {index}",
            "100",
            operation_id=f"settings-{customer_id}-{index}",
        )
    )


def test_default_target_and_permissions(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    admin = SettingsService(db_path, CurrentUser(1, "admin", "admin"))
    seller = SettingsService(db_path, CurrentUser(2, "seller", "seller"))

    assert admin.loyalty_target_purchase_count() == 6
    assert admin.can_open_settings() is True
    assert seller.can_open_settings() is False
    with pytest.raises(SettingsPermissionError):
        seller.save_settings({"loyalty_target_purchase_count": "8"})


def test_settings_page_shows_clear_loyalty_target_text_and_value(tmp_path) -> None:
    app = _app()
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    service = SettingsService(db_path)
    page = SettingsPage(service, lambda: None, lambda: None)
    page.show()
    app.processEvents()

    labels = [label.text() for label in page.findChildren(QLabel)]

    assert page.target_input.value() == 6
    assert any("Compras necesarias para obtener el premio" in text for text in labels)
    assert any("Cada compra agrega un cupón" in text for text in labels)
    assert page.target_current_label.text() == "Configuración actual: 6 compras por ciclo"
    assert "background: #ffffff" in page.target_input.styleSheet()
    assert "color: #252525" in page.target_input.styleSheet()

    page.target_input.setValue(8)
    app.processEvents()

    assert page.target_current_label.text() == "Configuración actual: 8 compras por ciclo"


def test_admin_changes_target_and_new_cycle_uses_it(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    settings = SettingsService(db_path)
    settings.save_settings({"loyalty_target_purchase_count": "8"})
    customer_id = _customer(db_path)
    purchase_service = PurchaseService(db_path, settings)

    result = _simple(purchase_service, customer_id, 1)

    assert result.target_purchase_count == 8
    assert result.missing_count == 7


def test_main_window_replaces_about_button_with_footer_label(tmp_path, monkeypatch) -> None:
    app = _app()
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    monkeypatch.setattr("app.ui.main_window.database_path", lambda: db_path)

    window = MainWindow()
    app.processEvents()

    button_texts = [button.text() for button in window.findChildren(QPushButton)]
    footer = window.findChild(QLabel, "FooterText")

    assert "Acerca de" not in button_texts
    assert "Cumpleaños del mes" in button_texts
    assert footer is not None
    assert f"Bella Vita · Club de Compras · Versión {VERSION}" in footer.text()
    assert "QCheckBox::indicator" in window._stylesheet()
    assert "border: 2px solid #4f5d5d" in window._stylesheet()
    assert "background: #2f6f73" in window._stylesheet()


def test_existing_cycle_keeps_target_after_setting_change(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    settings = SettingsService(db_path)
    customer_a = _customer(db_path, "099777001")
    purchase_service = PurchaseService(db_path, settings)

    first = _simple(purchase_service, customer_a, 1)
    settings.save_settings({"loyalty_target_purchase_count": "8"})
    last = first
    for index in range(2, 7):
        last = _simple(purchase_service, customer_a, index)

    assert first.target_purchase_count == 6
    assert last.cycle_completed is True
    assert last.target_purchase_count == 6
    assert last.reward_id is not None

    customer_b = _customer(db_path, "099777002")
    result = _simple(purchase_service, customer_b, 1)
    assert result.target_purchase_count == 8


def test_new_eight_target_cycle_completes_at_eight_not_six(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    settings = SettingsService(db_path)
    settings.save_settings({"loyalty_target_purchase_count": "8"})
    customer_id = _customer(db_path)
    purchase_service = PurchaseService(db_path, settings)

    sixth = None
    for index in range(1, 7):
        sixth = _simple(purchase_service, customer_id, index)
    assert sixth is not None
    assert sixth.cycle_completed is False
    assert sixth.reward_id is None

    seventh = _simple(purchase_service, customer_id, 7)
    eighth = _simple(purchase_service, customer_id, 8)
    assert seventh.cycle_completed is False
    assert eighth.cycle_completed is True
    assert eighth.target_purchase_count == 8
    with sqlite3.connect(db_path) as connection:
        rewards = connection.execute("SELECT COUNT(*) FROM rewards").fetchone()[0]
    assert rewards == 1
    reward = RewardService(db_path).list_rewards(status="available")[0]
    assert reward.max_value == eighth.cycle_average
    assert reward.target_purchase_count == 8


@pytest.mark.parametrize("target", ["0", "-1", "51"])
def test_rejects_invalid_targets(tmp_path, target: str) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    settings = SettingsService(db_path)

    with pytest.raises(SettingsValidationError):
        settings.save_settings({"loyalty_target_purchase_count": target})


def test_email_validation_and_persistence_and_audit(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    settings = SettingsService(db_path)

    settings.save_settings({"promotion_sender_email": "promo@example.com"})
    assert SettingsService(db_path).get_settings()["promotion_sender_email"] == "promo@example.com"
    with pytest.raises(SettingsValidationError):
        settings.save_settings({"promotion_sender_email": "correo-invalido"})
    with sqlite3.connect(db_path) as connection:
        actions = {
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_logs WHERE action IN ('SETTINGS_UPDATED', 'PROMOTION_EMAIL_SETTINGS_UPDATED')"
            )
        }
    assert {"SETTINGS_UPDATED", "PROMOTION_EMAIL_SETTINGS_UPDATED"} <= actions


def test_purchase_page_resets_after_save(tmp_path) -> None:
    app = _app()
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    customer_service = CustomerService(db_path)
    purchase_service = PurchaseService(db_path)
    saved_results = []
    page = PurchasePage(customer_service, purchase_service, lambda: None, saved_results.append)
    page.show()
    app.processEvents()

    page.preselect_customer(customer_id)
    page.summary_input.setText("Compra")
    page.amount_input.setText("100")
    result = purchase_service.register_purchase(
        purchase_service.build_simple_purchase(customer_id, "Compra", "100", operation_id="ui-flow")
    )
    saved_results.append(result)
    page.reset_for_next_purchase()
    app.processEvents()

    assert saved_results[0].sticker_number == 1
    assert page._selected_customer is None
    assert page.summary_input.text() == ""
    assert page.amount_input.text() == ""
    assert page.save_button.isEnabled() is False
    assert page.customer_search_input.hasFocus() is True


def test_same_operation_still_prevents_duplicate(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    purchase_service = PurchaseService(db_path)
    purchase = purchase_service.build_simple_purchase(customer_id, "Compra", "100", operation_id="same")

    first = purchase_service.register_purchase(purchase)
    second = purchase_service.register_purchase(purchase)

    assert first.purchase_id == second.purchase_id
    with sqlite3.connect(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
    assert count == 1
