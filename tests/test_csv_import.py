from __future__ import annotations

import csv
import sqlite3
from decimal import Decimal

import pytest

from app.database.schema import initialize_database
from app.repositories.loyalty import LoyaltyRepository
from app.services.birthday_promotions import BirthdayPromotionService
from app.services.csv_import import (
    CSV_IMPORT_HEADERS,
    CsvImportError,
    CsvImportService,
    parse_money,
    normalize_phone,
)
from app.services.customers import CustomerService
from app.services.settings import CurrentUser, SettingsService


def _csv(rows, delimiter=",") -> bytes:
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_IMPORT_HEADERS, delimiter=delimiter)
    writer.writeheader()
    for row in rows:
        complete = {header: "" for header in CSV_IMPORT_HEADERS}
        complete.update(row)
        writer.writerow(complete)
    return buffer.getvalue().encode("utf-8-sig")


def _counts(db_path):
    with sqlite3.connect(db_path) as connection:
        return {
            "customers": connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "purchases": connection.execute("SELECT COUNT(*) FROM purchases").fetchone()[0],
            "cycles": connection.execute("SELECT COUNT(*) FROM loyalty_cycles").fetchone()[0],
            "completed_cycles": connection.execute(
                "SELECT COUNT(*) FROM loyalty_cycles WHERE status = 'completed'"
            ).fetchone()[0],
            "rewards": connection.execute("SELECT COUNT(*) FROM rewards").fetchone()[0],
        }


def _service(db_path, user: CurrentUser | None = None) -> CsvImportService:
    return CsvImportService(db_path, user or CurrentUser(1, "admin", "admin"))


def test_import_customer_only_with_name_and_phone(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    service = _service(db_path)
    preview = service.analyze_bytes(_csv([{"Nombre": "María", "Telefono": "099012345"}]))

    result = service.import_preview(preview)
    customer = CustomerService(db_path).get_customer(1)

    assert result.customers_created == 1
    assert customer is not None
    assert customer.full_name == "María"
    assert customer.phone == "099012345"
    assert customer.last_name == ""
    assert customer.email is None
    assert customer.birth_date is None


def test_import_customer_with_one_purchase_and_text_phone(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    content = _csv(
        [
            {
                "Nombre": "Ana",
                "Telefono": "098 555 444",
                "Producto_1": "Remera",
                "Monto_1": "$ 1.500",
            }
        ]
    )
    result = _service(db_path).import_preview(_service(db_path).analyze_bytes(content))

    customer = CustomerService(db_path).get_customer(1)
    assert result.purchases_created == 1
    assert customer.phone == "098 555 444"
    assert customer.current_stickers == 1
    assert customer.current_cycle_total == "1500"


def test_import_six_purchases_completes_cycle_and_reward_when_target_is_six(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    row = {"Nombre": "Ciclo", "Telefono": "099111222"}
    for index, amount in enumerate(["1000", "1500", "2000", "1200", "1800", "1500"], start=1):
        row[f"Producto_{index}"] = f"Producto {index}"
        row[f"Monto_{index}"] = amount

    result = _service(db_path).import_preview(_service(db_path).analyze_bytes(_csv([row])))
    loyalty = LoyaltyRepository(db_path).summary_for_customer(1)

    assert result.purchases_created == 6
    assert result.cycles_completed == 1
    assert result.rewards_created == 1
    assert loyalty.available_rewards == 1
    with sqlite3.connect(db_path) as connection:
        average, reward_value = connection.execute(
            """
            SELECT lc.average_amount, r.max_value
            FROM loyalty_cycles lc
            JOIN rewards r ON r.cycle_id = lc.id
            WHERE lc.customer_id = 1
            """
        ).fetchone()
    assert Decimal(str(average)).quantize(Decimal("0.01")) == Decimal("1500.00")
    assert Decimal(str(reward_value)).quantize(Decimal("0.01")) == Decimal("1500.00")


def test_import_six_purchases_does_not_complete_when_target_is_eight(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    SettingsService(db_path).save_settings({"loyalty_target_purchase_count": "8"})
    row = {"Nombre": "Objetivo", "Telefono": "099222333"}
    for index in range(1, 7):
        row[f"Producto_{index}"] = f"Producto {index}"
        row[f"Monto_{index}"] = "1000"

    result = _service(db_path).import_preview(_service(db_path).analyze_bytes(_csv([row])))
    customer = CustomerService(db_path).get_customer(1)

    assert result.purchases_created == 6
    assert result.rewards_created == 0
    assert customer.current_stickers == 6
    assert customer.current_cycle_target == 8
    assert _counts(db_path)["completed_cycles"] == 0


@pytest.mark.parametrize(
    ("product", "amount", "message"),
    [
        ("Blusa", "", "Producto_1 informado sin Monto_1"),
        ("", "1000", "Monto_1 informado sin Producto_1"),
        ("Blusa", "0", "Monto_1 debe ser mayor que cero"),
        ("Blusa", "-1", "Monto_1 debe ser mayor que cero"),
    ],
)
def test_purchase_pair_validation_errors(tmp_path, product: str, amount: str, message: str) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    preview = _service(db_path).analyze_bytes(
        _csv([{"Nombre": "Error", "Telefono": "099333444", "Producto_1": product, "Monto_1": amount}])
    )

    assert preview.rows[0].status == "Error"
    assert any(message in item for item in preview.rows[0].messages)


def test_money_parser_accepts_uruguayan_formats() -> None:
    assert parse_money("1500") == Decimal("1500.00")
    assert parse_money("1500.50") == Decimal("1500.50")
    assert parse_money("1500,50") == Decimal("1500.50")
    assert parse_money("$ 1.500") == Decimal("1500.00")
    assert parse_money("$1.500,50") == Decimal("1500.50")


def test_existing_customer_updates_empty_fields_and_does_not_overwrite_conflicts(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_service = CustomerService(db_path)
    customer_id = customer_service.create_customer(
        customer_service.build_customer("Lucía", "", "099444555", "cliente@gmail.com", "", False)
    ).customer_id
    content = _csv(
        [
            {
                "Nombre": "Lucía",
                "Apellido": "Silva",
                "Telefono": "099 444 555",
                "Correo": "otro@gmail.com",
                "Producto_1": "Vestido",
                "Monto_1": "1200",
            }
        ]
    )
    service = _service(db_path)
    preview = service.analyze_bytes(content)
    result = service.import_preview(preview)
    customer = customer_service.get_customer(customer_id)

    assert preview.rows[0].status == "Advertencia"
    assert result.customers_created == 0
    assert result.customers_updated == 1
    assert _counts(db_path)["customers"] == 1
    assert customer.last_name == "Silva"
    assert customer.email == "cliente@gmail.com"
    assert customer.current_stickers == 1
    assert normalize_phone("+598 99 444 555") == "59899444555"


def test_duplicate_file_is_detected_and_reimport_does_not_duplicate_purchases(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    content = _csv([{"Nombre": "Doble", "Telefono": "099555666", "Producto_1": "Blusa", "Monto_1": "1000"}])
    service = _service(db_path)
    preview = service.analyze_bytes(content, "clientes.csv")
    first = service.import_preview(preview)
    duplicate_preview = service.analyze_bytes(content, "clientes.csv")
    blocked = service.import_preview(duplicate_preview)
    forced = service.import_preview(duplicate_preview, allow_reimport=True)

    assert first.purchases_created == 1
    assert duplicate_preview.duplicate_batch_message is not None
    assert blocked.rows_skipped == 1
    assert forced.purchases_created == 0
    assert _counts(db_path)["purchases"] == 1


def test_invalid_row_is_not_imported_but_valid_rows_are_partial(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    preview = _service(db_path).analyze_bytes(
        _csv(
            [
                {"Nombre": "Valida", "Telefono": "099666777"},
                {"Nombre": "SinTelefono", "Telefono": ""},
            ]
        )
    )
    result = _service(db_path).import_preview(preview, mode="partial")

    assert result.customers_created == 1
    assert result.rows_error == 1
    assert _counts(db_path)["customers"] == 1


def test_all_or_nothing_cancels_when_there_are_errors(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    preview = _service(db_path).analyze_bytes(
        _csv([{"Nombre": "Valida", "Telefono": "099666777"}, {"Nombre": "", "Telefono": "099"}])
    )
    result = _service(db_path).import_preview(preview, mode="all_or_nothing")

    assert result.customers_created == 0
    assert result.rows_error == 1
    assert _counts(db_path)["customers"] == 0


def test_template_report_semicolon_csv_dates_and_audit(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    service = _service(db_path)
    template, instructions = service.write_template(tmp_path)
    content = _csv(
        [
            {
                "Nombre": "Ñata",
                "Telefono": "099777888",
                "Fecha_Nacimiento": "14/08/1985",
                "Consentimiento_Promociones": "SÍ",
            },
            {"Nombre": "Iso", "Telefono": "099777889", "Fecha_Nacimiento": "1985-08-15"},
        ],
        delimiter=";",
    )
    preview = service.analyze_bytes(content)
    result = service.import_preview(preview)
    report = service.write_result_report(result, tmp_path / "reporte.csv")

    assert template.read_bytes().startswith(b"\xef\xbb\xbf")
    assert instructions.exists()
    assert report.exists()
    assert preview.rows[0].birth_date == "1985-08-14"
    assert preview.rows[1].birth_date == "1985-08-15"
    assert CustomerService(db_path).get_customer(1).marketing_consent is True
    with sqlite3.connect(db_path) as connection:
        actions = {row[0] for row in connection.execute("SELECT action FROM audit_logs").fetchall()}
    assert {"CSV_IMPORT_STARTED", "CSV_IMPORT_COMPLETED", "CUSTOMER_IMPORTED"} <= actions


def test_semicolon_csv_with_many_empty_columns_uses_delimiter_fallback(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    content = (
        "Nombre;Apellido;Telefono;Correo;Fecha_Nacimiento;Consentimiento_Promociones;Producto_1;Monto_1;Producto_2;Monto_2;Producto_3;Monto_3;Producto_4;Monto_4;Producto_5;Monto_5;Producto_6;Monto_6;Observaciones\n"
        "Solo;;099123123;;;;;;;;;;;;;;;;\n"
    ).encode("utf-8-sig")

    preview = _service(db_path).analyze_bytes(content)

    assert preview.rows[0].first_name == "Solo"
    assert preview.rows[0].phone == "099123123"


def test_future_birth_date_rejected_and_birth_without_consent_excluded_from_promotions(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    preview = _service(db_path).analyze_bytes(
        _csv(
            [
                {"Nombre": "Fecha", "Telefono": "099888999", "Fecha_Nacimiento": "14/08/1985"},
                {"Nombre": "Futura", "Telefono": "099888000", "Fecha_Nacimiento": "01/01/2999"},
            ]
        )
    )
    result = _service(db_path).import_preview(preview)

    assert result.customers_created == 1
    assert result.rows_error == 1
    assert CustomerService(db_path).get_customer(1).birth_date == "1985-08-14"
    assert BirthdayPromotionService(db_path).customers_for_month(8) == []


def test_only_admin_can_import(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    seller = CsvImportService(db_path, CurrentUser(2, "seller", "seller"))

    with pytest.raises(CsvImportError):
        seller.analyze_bytes(_csv([{"Nombre": "Vendedor", "Telefono": "099"}]))
