from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.utils.money import money_from_db


@dataclass(frozen=True)
class PurchaseHistoryRow:
    id: int
    purchased_at: str
    cycle_number: int
    sticker_number: int
    summary: str
    total_amount: Decimal
    status: str


@dataclass(frozen=True)
class CycleHistoryRow:
    id: int
    cycle_number: int
    started_at: str
    completed_at: str | None
    target_purchase_count: int
    valid_purchase_count: int
    total_amount: Decimal
    average_amount: Decimal
    status: str


@dataclass(frozen=True)
class RewardHistoryRow:
    id: int
    cycle_number: int
    earned_at: str
    max_value: Decimal
    status: str
    used_at: str | None
    delivered_item_description: str | None


class CustomerHistoryRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def purchases(self, customer_id: int) -> list[PurchaseHistoryRow]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, purchased_at, cycle_number, sticker_number, summary, total_amount, status
                FROM purchases
                WHERE customer_id = ?
                ORDER BY purchased_at DESC, id DESC
                """,
                (customer_id,),
            ).fetchall()
        return [
            PurchaseHistoryRow(row[0], row[1], row[2], row[3], row[4], money_from_db(row[5]), row[6])
            for row in rows
        ]

    def cycles(self, customer_id: int) -> list[CycleHistoryRow]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, cycle_number, started_at, completed_at, target_purchase_count, valid_purchase_count,
                       total_amount, average_amount, status
                FROM loyalty_cycles
                WHERE customer_id = ?
                ORDER BY cycle_number DESC
                """,
                (customer_id,),
            ).fetchall()
        return [
            CycleHistoryRow(
                row[0], row[1], row[2], row[3], row[4], row[5], money_from_db(row[6]), money_from_db(row[7]), row[8]
            )
            for row in rows
        ]

    def rewards(self, customer_id: int) -> list[RewardHistoryRow]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT r.id, lc.cycle_number, r.earned_at, r.max_value, r.status,
                       r.used_at, r.delivered_item_description
                FROM rewards r
                JOIN loyalty_cycles lc ON lc.id = r.cycle_id
                WHERE r.customer_id = ?
                ORDER BY r.earned_at DESC, r.id DESC
                """,
                (customer_id,),
            ).fetchall()
        return [
            RewardHistoryRow(row[0], row[1], row[2], money_from_db(row[3]), row[4], row[5], row[6])
            for row in rows
        ]
