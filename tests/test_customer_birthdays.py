from __future__ import annotations

import csv
import os
import sqlite3
from datetime import date, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.database.schema import initialize_database
from app.services.birthday_promotions import BirthdayPromotionService
from app.services.customers import CustomerService, CustomerValidationError
from app.ui.customer_dialog import CustomerDialog


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _service(db_path) -> CustomerService:
    return CustomerService(db_path)


def _create_customer(db_path, name: str, birth_date: str | None, consent: bool = True) -> int:
    service = _service(db_path)
    return service.create_customer(
        service.build_customer(
            first_name=name,
            last_name="Birthday",
            phone=f"099{name}",
            email=f"{name.lower()}@example.com",
            notes="",
            marketing_consent=consent,
            birth_date=birth_date or "",
        )
    ).customer_id


def test_create_customer_without_birth_date_does_not_default_to_today(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _create_customer(db_path, "SinFecha", None)

    customer = _service(db_path).get_customer(customer_id)

    assert customer is not None
    assert customer.birth_date is None


def test_create_edit_clear_and_persist_birth_date(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    service = _service(db_path)
    customer_id = _create_customer(db_path, "Fecha", "1985-08-14")

    saved = CustomerService(db_path).get_customer(customer_id)
    assert saved is not None
    assert saved.birth_date == "1985-08-14"

    updated = service.build_customer("Fecha", "Birthday", "099Fecha", "fecha@example.com", "", True, birth_date="1990-09-10")
    service.update_customer(customer_id, updated)
    assert CustomerService(db_path).get_customer(customer_id).birth_date == "1990-09-10"

    cleared = service.build_customer("Fecha", "Birthday", "099Fecha", "fecha@example.com", "", True, birth_date="")
    service.update_customer(customer_id, cleared)
    assert CustomerService(db_path).get_customer(customer_id).birth_date is None


@pytest.mark.parametrize("birth_date", ["2999-01-01", "1899-12-31"])
def test_rejects_future_and_too_old_birth_dates(tmp_path, birth_date: str) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)

    with pytest.raises(CustomerValidationError):
        _service(db_path).build_customer("Mala", "Fecha", "099111222", "", "", False, birth_date=birth_date)


def test_birth_date_migration_is_idempotent_and_preserves_existing_clients(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                notes TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                marketing_consent INTEGER NOT NULL DEFAULT 0,
                marketing_consent_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "INSERT INTO customers (first_name, last_name, phone) VALUES ('Viejo', 'Cliente', '099000')"
        )

    initialize_database(db_path)
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(customers)")}
        row = connection.execute("SELECT first_name, birth_date FROM customers WHERE id = 1").fetchone()

    assert "birth_date" in columns
    assert row == ("Viejo", None)


def test_birthday_month_filters_and_consent_active_rules(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    august_id = _create_customer(db_path, "Agosto", "1985-08-14", consent=True)
    _create_customer(db_path, "Septiembre", "1985-09-14", consent=True)
    no_consent_id = _create_customer(db_path, "SinConsent", "1985-08-20", consent=False)
    inactive_id = _create_customer(db_path, "Inactivo", "1985-08-21", consent=True)
    CustomerService(db_path).set_customer_active(inactive_id, False)

    service = BirthdayPromotionService(db_path)

    assert [customer.id for customer in service.customers_for_month(8)] == [august_id, no_consent_id]
    assert [customer.id for customer in service.customers_for_month(9)] != [august_id]
    assert [customer.id for customer in service.customers_for_month(8, require_marketing_consent=True)] == [august_id]


def test_today_week_and_next_month_filters_crossing_year(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _create_customer(db_path, "Hoy", "1980-12-30")
    _create_customer(db_path, "Semana", "1980-01-02")
    _create_customer(db_path, "ProximoMes", "1980-01-15")
    service = BirthdayPromotionService(db_path)

    today = date(2026, 12, 30)

    assert [customer.first_name for customer in service.birthdays_today(today)] == ["Hoy"]
    assert {customer.first_name for customer in service.birthdays_this_week(today)} == {"Hoy", "Semana"}
    assert {customer.first_name for customer in service.birthdays_next_month(today)} == {"Semana", "ProximoMes"}


def test_dashboard_counts_birthdays_this_month(tmp_path, monkeypatch) -> None:
    from app.repositories import dashboard as dashboard_module

    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    current_month = date.today().month
    _create_customer(db_path, "MesActual", f"1980-{current_month:02d}-10")
    _create_customer(db_path, "OtroMes", "1980-01-10" if current_month != 1 else "1980-02-10")

    stats = dashboard_module.DashboardRepository(db_path).stats()

    assert stats.birthdays_this_month == 1
    assert stats.upcoming_birthdays


def test_birthdays_export_includes_expected_columns(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _create_customer(db_path, "Exportar", "1985-08-14")
    output = tmp_path / "cumples_agosto.csv"

    BirthdayPromotionService(db_path).export_month(8, output)

    with output.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["Fecha de nacimiento"] == "1985-08-14"
    assert rows[0]["Día de cumpleaños"] == "14"
    assert rows[0]["Mes de cumpleaños"] == "Agosto"


def test_customer_dialog_birth_date_is_empty_by_default(tmp_path) -> None:
    app = _app()
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    dialog = CustomerDialog(CustomerService(db_path))
    dialog.show()
    app.processEvents()

    assert dialog.birth_date_empty_input.isChecked() is True
    assert dialog._birth_date_value() == ""
