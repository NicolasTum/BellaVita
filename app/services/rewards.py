from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.repositories.rewards import RewardRecord, RewardRepository
from app.utils.money import money_to_db, to_decimal


class RewardValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RewardRedeemInput:
    reward_id: int
    delivered_item_description: str
    delivered_item_price: Decimal
    paid_difference: Decimal
    notes: str | None
    user_id: int | None = None


@dataclass(frozen=True)
class RewardRedeemResult:
    reward_id: int
    customer_id: int
    status: str
    used_at: str


class RewardService:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._repository = RewardRepository(database_path)

    def list_rewards(self, status: str = "available", search: str = "") -> list[RewardRecord]:
        return self._repository.list_rewards(status=status, search=search)

    def get_reward(self, reward_id: int) -> RewardRecord | None:
        return self._repository.get(reward_id)

    def build_redeem_input(
        self,
        reward_id: int,
        delivered_item_description: str,
        delivered_item_price: str,
        paid_difference: str,
        notes: str = "",
        user_id: int | None = None,
    ) -> RewardRedeemInput:
        description = delivered_item_description.strip()
        if not description:
            raise RewardValidationError("La prenda entregada es obligatoria.")
        price = to_decimal(delivered_item_price)
        difference = to_decimal(paid_difference or "0")
        if price <= 0:
            raise RewardValidationError("El precio de la prenda debe ser mayor que cero.")
        if difference < 0:
            raise RewardValidationError("La diferencia pagada no puede ser negativa.")
        return RewardRedeemInput(
            reward_id=reward_id,
            delivered_item_description=description,
            delivered_item_price=price,
            paid_difference=difference,
            notes=notes.strip() or None,
            user_id=user_id,
        )

    def redeem_reward(self, data: RewardRedeemInput) -> RewardRedeemResult:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute("BEGIN IMMEDIATE")
            reward = connection.execute(
                """
                SELECT id, customer_id, max_value, status
                FROM rewards
                WHERE id = ?
                """,
                (data.reward_id,),
            ).fetchone()
            if not reward:
                raise RewardValidationError("El premio no existe.")
            reward_id, customer_id, max_value_raw, status = reward
            max_value = to_decimal(str(max_value_raw))
            if status != "available":
                self._audit(
                    connection,
                    data.user_id,
                    "REWARD_REDEEM_ATTEMPT_REJECTED",
                    "rewards",
                    reward_id,
                    f"customer_id={customer_id};status={status}",
                )
                connection.commit()
                raise RewardValidationError("Este premio ya no está disponible.")

            required_difference = max(Decimal("0.00"), data.delivered_item_price - max_value)
            if data.paid_difference < required_difference:
                self._audit(
                    connection,
                    data.user_id,
                    "REWARD_REDEEM_ATTEMPT_REJECTED",
                    "rewards",
                    reward_id,
                    f"customer_id={customer_id};required_difference={required_difference};paid={data.paid_difference}",
                )
                connection.commit()
                raise RewardValidationError(
                    "La diferencia pagada no cubre el exceso sobre el valor del premio."
                )

            connection.execute(
                """
                UPDATE rewards
                SET status = 'used',
                    used_at = CURRENT_TIMESTAMP,
                    delivered_item_description = ?,
                    delivered_item_price = ?,
                    value_difference = ?,
                    notes = ?,
                    delivered_by_user_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    data.delivered_item_description,
                    money_to_db(data.delivered_item_price),
                    money_to_db(data.paid_difference),
                    data.notes,
                    data.user_id,
                    reward_id,
                ),
            )
            used_at = connection.execute("SELECT used_at FROM rewards WHERE id = ?", (reward_id,)).fetchone()[0]
            self._audit(
                connection,
                data.user_id,
                "REWARD_REDEEMED",
                "rewards",
                reward_id,
                f"customer_id={customer_id};item={data.delivered_item_description};price={data.delivered_item_price};difference={data.paid_difference}",
            )
            return RewardRedeemResult(
                reward_id=reward_id,
                customer_id=customer_id,
                status="used",
                used_at=used_at,
            )

    def _audit(
        self,
        connection: sqlite3.Connection,
        user_id: int | None,
        action: str,
        entity: str,
        entity_id: int,
        new_value: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity, entity_id, new_value)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, action, entity, entity_id, new_value),
        )
