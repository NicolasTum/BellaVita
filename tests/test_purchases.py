from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest

from app.config.settings import SETTINGS
from app.database.schema import initialize_database
from app.repositories.loyalty import LoyaltyRepository
from app.services.customers import CustomerService
from app.services.purchases import PurchaseService, PurchaseValidationError


def _customer(db_path, active: bool = True) -> int:
    service = CustomerService(db_path)
    customer = service.build_customer(
        first_name="Cliente",
        last_name="Prueba",
        phone="099000000",
        email="",
        notes="",
        marketing_consent=False,
    )
    customer_id = service.create_customer(customer).customer_id
    if not active:
        service.set_customer_active(customer_id, False)
    return customer_id


def _simple(service: PurchaseService, customer_id: int, amount: str, op: str):
    purchase = service.build_simple_purchase(
        customer_id=customer_id,
        summary=f"Compra {amount}",
        total_amount=amount,
        operation_id=op,
    )
    return service.register_purchase(purchase)


def _counts(db_path):
    with sqlite3.connect(db_path) as connection:
        return {
            "cycles": connection.execute("SELECT COUNT(*) FROM loyalty_cycles").fetchone()[0],
            "purchases": connection.execute("SELECT COUNT(*) FROM purchases").fetchone()[0],
            "rewards": connection.execute("SELECT COUNT(*) FROM rewards").fetchone()[0],
        }


def test_first_purchase_creates_cycle_and_sticker_one(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    result = _simple(service, customer_id, "1000", "op-1")

    assert result.cycle_number == 1
    assert result.sticker_number == 1
    assert result.missing_count == SETTINGS.stickers_per_cycle - 1
    assert _counts(db_path)["cycles"] == 1


def test_second_purchase_is_sticker_two(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    _simple(service, customer_id, "1000", "op-1")
    result = _simple(service, customer_id, "1500", "op-2")

    assert result.sticker_number == 2
    assert result.cycle_number == 1


def test_five_purchases_do_not_create_reward(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    for index in range(5):
        _simple(service, customer_id, "1000", f"op-{index}")

    assert _counts(db_path)["rewards"] == 0


def test_sixth_purchase_completes_cycle_and_creates_single_reward(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)
    amounts = ["1000", "1500", "2000", "1200", "1800", "1500"]

    result = None
    for index, amount in enumerate(amounts):
        result = _simple(service, customer_id, amount, f"op-{index}")

    assert result is not None
    assert result.cycle_completed is True
    assert result.cycle_total == Decimal("9000.00")
    assert result.cycle_average == Decimal("1500.00")
    assert result.reward_value == Decimal("1500.00")
    assert _counts(db_path)["rewards"] == 1

    loyalty = LoyaltyRepository(db_path).summary_for_customer(customer_id)
    assert loyalty.available_rewards == 1
    assert _counts(db_path)["rewards"] == 1


def test_retrying_sixth_purchase_does_not_duplicate_reward(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    for index in range(5):
        _simple(service, customer_id, "1000", f"retry-{index}")
    sixth = service.build_simple_purchase(customer_id, "Compra final", "1000", operation_id="retry-six")

    first = service.register_purchase(sixth)
    second = service.register_purchase(sixth)

    assert first.purchase_id == second.purchase_id
    assert _counts(db_path)["purchases"] == 6
    assert _counts(db_path)["rewards"] == 1


def test_seventh_purchase_starts_new_cycle_with_pending_reward(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    for index in range(6):
        _simple(service, customer_id, "1000", f"op-{index}")
    result = _simple(service, customer_id, "700", "op-7")

    assert result.cycle_number == 2
    assert result.sticker_number == 1
    loyalty = LoyaltyRepository(db_path).summary_for_customer(customer_id)
    assert loyalty.available_rewards == 1
    assert loyalty.current_cycle is not None
    assert loyalty.current_cycle.cycle_number == 2


def test_inactive_customer_cannot_purchase(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path, active=False)
    service = PurchaseService(db_path)
    purchase = service.build_simple_purchase(customer_id, "Compra", "1000", operation_id="inactive")

    with pytest.raises(PurchaseValidationError):
        service.register_purchase(purchase)


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_zero_and_negative_amount_rejected(tmp_path, amount: str) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    with pytest.raises(PurchaseValidationError):
        service.build_simple_purchase(customer_id, "Compra", amount)


def test_same_operation_id_does_not_duplicate_purchase(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)
    purchase = service.build_simple_purchase(customer_id, "Compra", "1000", operation_id="same-op")

    first = service.register_purchase(purchase)
    second = service.register_purchase(purchase)

    assert first.purchase_id == second.purchase_id
    assert _counts(db_path)["purchases"] == 1


def test_detailed_purchase_calculates_subtotals(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    purchase = service.build_detailed_purchase(
        customer_id,
        [("Camisa", "2", "500"), ("Pantalon", "1", "1200")],
        operation_id="detail",
    )
    result = service.register_purchase(purchase)

    assert purchase.total_amount == Decimal("2200.00")
    assert result.total_amount == Decimal("2200.00")
    with sqlite3.connect(db_path) as connection:
        subtotals = [
            row[0]
            for row in connection.execute(
                "SELECT subtotal FROM purchase_items ORDER BY id"
            ).fetchall()
        ]
    assert subtotals == [1000, 1200]


def test_simple_purchase_persists_after_reopening_database(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    _simple(service, customer_id, "999.50", "persist")
    reopened = LoyaltyRepository(db_path).summary_for_customer(customer_id)

    assert reopened.current_cycle is not None
    assert reopened.current_cycle.total_amount == Decimal("999.50")
    assert reopened.stickers[0].summary == "Compra 999.50"


def test_customer_summary_updates_after_purchase(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    purchase_service = PurchaseService(db_path)
    customer_service = CustomerService(db_path)

    _simple(purchase_service, customer_id, "1000", "summary")
    customer = customer_service.get_customer(customer_id)

    assert customer is not None
    assert customer.current_stickers == 1
    assert customer.current_cycle_total == "1000"
    assert customer.current_cycle_average == "1000"


def test_audit_records_purchase_cycle_and_reward(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id = _customer(db_path)
    service = PurchaseService(db_path)

    for index in range(6):
        _simple(service, customer_id, "1000", f"audit-{index}")

    with sqlite3.connect(db_path) as connection:
        actions = {
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_logs WHERE action IN ('PURCHASE_CREATED', 'CYCLE_CREATED', 'CYCLE_COMPLETED', 'REWARD_CREATED')"
            ).fetchall()
        }

    assert {"PURCHASE_CREATED", "CYCLE_CREATED", "CYCLE_COMPLETED", "REWARD_CREATED"} <= actions
