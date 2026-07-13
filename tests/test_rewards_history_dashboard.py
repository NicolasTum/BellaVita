from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest

from app.database.schema import initialize_database
from app.repositories.dashboard import DashboardRepository
from app.repositories.history import CustomerHistoryRepository
from app.services.customers import CustomerService
from app.services.purchases import PurchaseService
from app.services.rewards import RewardService, RewardValidationError


def _customer(db_path, phone: str = "099555000") -> int:
    service = CustomerService(db_path)
    return service.create_customer(
        service.build_customer("Premio", "Cliente", phone, "premio@example.com", "", False)
    ).customer_id


def _reward(db_path) -> tuple[int, int]:
    customer_id = _customer(db_path)
    purchases = PurchaseService(db_path)
    for index in range(6):
        purchases.register_purchase(
            purchases.build_simple_purchase(
                customer_id,
                f"Compra {index + 1}",
                "1500",
                operation_id=f"reward-{index}",
            )
        )
    reward = RewardService(db_path).list_rewards(status="available")[0]
    return customer_id, reward.id


def _user(db_path) -> int:
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, display_name, password_hash, role, must_change_password)
            VALUES ('seller', 'Vendedor', 'hash', 'seller', 0)
            """
        )
        return int(cursor.lastrowid)


def test_reward_listing_filter_and_search(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _reward(db_path)
    service = RewardService(db_path)

    available = service.list_rewards(status="available")
    used = service.list_rewards(status="used")
    searched = service.list_rewards(status="available", search="Premio")

    assert len(available) == 1
    assert used == []
    assert len(searched) == 1
    assert searched[0].max_value == Decimal("1500.00")
    assert searched[0].target_purchase_count == 6


@pytest.mark.parametrize("price,difference", [("1000", "0"), ("1500", "0"), ("1800", "300")])
def test_valid_reward_redemptions(tmp_path, price: str, difference: str) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id, reward_id = _reward(db_path)
    user_id = _user(db_path)
    service = RewardService(db_path)

    data = service.build_redeem_input(
        reward_id,
        "Remera",
        price,
        difference,
        "Canje de prueba",
        user_id=user_id,
    )
    result = service.redeem_reward(data)
    reward = service.get_reward(reward_id)

    assert result.customer_id == customer_id
    assert result.status == "used"
    assert result.used_at
    assert reward is not None
    assert reward.status == "used"
    assert reward.used_at is not None
    assert reward.delivered_by_user_id == user_id
    assert reward.delivered_item_description == "Remera"


def test_rejects_insufficient_difference_and_audits(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _, reward_id = _reward(db_path)
    service = RewardService(db_path)
    data = service.build_redeem_input(reward_id, "Campera", "1800", "200")

    with pytest.raises(RewardValidationError):
        service.redeem_reward(data)

    with sqlite3.connect(db_path) as connection:
        action = connection.execute(
            "SELECT action FROM audit_logs WHERE action = 'REWARD_REDEEM_ATTEMPT_REJECTED'"
        ).fetchone()[0]
    assert action == "REWARD_REDEEM_ATTEMPT_REJECTED"


@pytest.mark.parametrize("price,difference", [("0", "0"), ("1000", "-1")])
def test_redeem_validation_rejects_invalid_amounts(tmp_path, price: str, difference: str) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _, reward_id = _reward(db_path)
    service = RewardService(db_path)

    with pytest.raises(RewardValidationError):
        service.build_redeem_input(reward_id, "Remera", price, difference)


def test_rejects_second_redemption(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _, reward_id = _reward(db_path)
    service = RewardService(db_path)
    data = service.build_redeem_input(reward_id, "Remera", "1000", "0")

    service.redeem_reward(data)
    with pytest.raises(RewardValidationError):
        service.redeem_reward(data)


def test_redemption_persists_and_audits(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _, reward_id = _reward(db_path)
    user_id = _user(db_path)
    service = RewardService(db_path)

    service.redeem_reward(service.build_redeem_input(reward_id, "Remera", "1000", "0", user_id=user_id))
    reopened = RewardService(db_path).get_reward(reward_id)

    assert reopened is not None
    assert reopened.status == "used"
    assert reopened.used_at is not None
    assert reopened.delivered_by_user_id == user_id
    with sqlite3.connect(db_path) as connection:
        action = connection.execute(
            "SELECT action FROM audit_logs WHERE action = 'REWARD_REDEEMED'"
        ).fetchone()[0]
    assert action == "REWARD_REDEEMED"


def test_customer_history_queries(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_id, reward_id = _reward(db_path)
    service = RewardService(db_path)
    service.redeem_reward(service.build_redeem_input(reward_id, "Remera", "1000", "0"))
    history = CustomerHistoryRepository(db_path)

    assert len(history.purchases(customer_id)) == 6
    assert len(history.cycles(customer_id)) == 1
    assert len(history.rewards(customer_id)) == 1
    assert history.rewards(customer_id)[0].status == "used"


def test_dashboard_stats_are_real(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _reward(db_path)
    customer_id = _customer(db_path, "099555001")
    purchase_service = PurchaseService(db_path)
    for index in range(5):
        purchase_service.register_purchase(
            purchase_service.build_simple_purchase(customer_id, f"Compra {index}", "100", operation_id=f"near-{index}")
        )

    stats = DashboardRepository(db_path).stats()

    assert stats.rewards_available == 1
    assert stats.rewards_available_value == Decimal("1500.00")
    assert stats.rewards_used == 0
    assert stats.cycles_near_completion == 1
    assert stats.purchases_today == 11


def test_reward_page_refresh_after_redemption(tmp_path) -> None:
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    _, reward_id = _reward(db_path)
    service = RewardService(db_path)

    assert len(service.list_rewards(status="available")) == 1
    service.redeem_reward(service.build_redeem_input(reward_id, "Remera", "1000", "0"))

    assert service.list_rewards(status="available") == []
    assert len(service.list_rewards(status="used")) == 1
