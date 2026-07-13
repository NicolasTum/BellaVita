from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.utils.money import money_from_db


@dataclass(frozen=True)
class RewardRecord:
    id: int
    customer_id: int
    customer_name: str
    phone: str | None
    email: str | None
    cycle_number: int
    target_purchase_count: int
    cycle_id: int
    earned_at: str
    max_value: Decimal
    status: str
    used_at: str | None
    delivered_item_description: str | None
    delivered_item_price: Decimal | None
    value_difference: Decimal | None
    notes: str | None
    delivered_by_user_id: int | None
    created_at: str
    updated_at: str


class RewardRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def list_rewards(self, status: str = "available", search: str = "") -> list[RewardRecord]:
        parameters: list[str] = []
        clauses: list[str] = []
        if status != "all":
            clauses.append("r.status = ?")
            parameters.append(status)
        cleaned = search.strip().lower()
        if cleaned:
            like = f"%{cleaned}%"
            clauses.append(
                """
                (
                    lower(c.first_name) LIKE ?
                    OR lower(c.last_name) LIKE ?
                    OR lower(c.first_name || ' ' || c.last_name) LIKE ?
                    OR lower(COALESCE(c.phone, '')) LIKE ?
                    OR lower(COALESCE(c.email, '')) LIKE ?
                )
                """
            )
            parameters.extend([like, like, like, like, like])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    r.id, r.customer_id, c.first_name || ' ' || c.last_name AS customer_name,
                    c.phone, c.email, lc.cycle_number, lc.target_purchase_count,
                    r.cycle_id, r.earned_at,
                    r.max_value, r.status, r.used_at, r.delivered_item_description,
                    r.delivered_item_price, r.value_difference, r.notes,
                    r.delivered_by_user_id, r.created_at, r.updated_at
                FROM rewards r
                JOIN customers c ON c.id = r.customer_id
                JOIN loyalty_cycles lc ON lc.id = r.cycle_id
                {where}
                ORDER BY r.earned_at DESC, r.id DESC
                """,
                parameters,
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def get(self, reward_id: int) -> RewardRecord | None:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    r.id, r.customer_id, c.first_name || ' ' || c.last_name AS customer_name,
                    c.phone, c.email, lc.cycle_number, lc.target_purchase_count,
                    r.cycle_id, r.earned_at,
                    r.max_value, r.status, r.used_at, r.delivered_item_description,
                    r.delivered_item_price, r.value_difference, r.notes,
                    r.delivered_by_user_id, r.created_at, r.updated_at
                FROM rewards r
                JOIN customers c ON c.id = r.customer_id
                JOIN loyalty_cycles lc ON lc.id = r.cycle_id
                WHERE r.id = ?
                """,
                (reward_id,),
            ).fetchone()
        return self._record_from_row(row) if row else None

    @staticmethod
    def _record_from_row(row) -> RewardRecord:
        return RewardRecord(
            id=row[0],
            customer_id=row[1],
            customer_name=row[2],
            phone=row[3],
            email=row[4],
            cycle_number=row[5],
            target_purchase_count=row[6],
            cycle_id=row[7],
            earned_at=row[8],
            max_value=money_from_db(row[9]),
            status=row[10],
            used_at=row[11],
            delivered_item_description=row[12],
            delivered_item_price=money_from_db(row[13]) if row[13] is not None else None,
            value_difference=money_from_db(row[14]) if row[14] is not None else None,
            notes=row[15],
            delivered_by_user_id=row[16],
            created_at=row[17],
            updated_at=row[18],
        )
