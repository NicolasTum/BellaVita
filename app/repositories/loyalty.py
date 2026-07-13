from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.config.settings import SETTINGS
from app.utils.money import money_from_db


@dataclass(frozen=True)
class CycleSummary:
    id: int
    customer_id: int
    cycle_number: int
    status: str
    valid_purchase_count: int
    total_amount: Decimal
    average_amount: Decimal
    started_at: str
    completed_at: str | None


@dataclass(frozen=True)
class StickerSummary:
    sticker_number: int
    purchased_at: str | None
    summary: str | None
    total_amount: Decimal | None


@dataclass(frozen=True)
class CustomerLoyaltySummary:
    current_cycle: CycleSummary | None
    latest_cycle: CycleSummary | None
    completed_cycles: int
    available_rewards: int
    last_purchase_at: str | None
    stickers: list[StickerSummary]


class LoyaltyRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def summary_for_customer(self, customer_id: int) -> CustomerLoyaltySummary:
        with sqlite3.connect(self._database_path) as connection:
            current_cycle = self._fetch_cycle(
                connection,
                """
                SELECT id, customer_id, cycle_number, status, valid_purchase_count,
                       total_amount, average_amount, started_at, completed_at
                FROM loyalty_cycles
                WHERE customer_id = ? AND status = 'in_progress'
                ORDER BY cycle_number DESC
                LIMIT 1
                """,
                (customer_id,),
            )
            latest_cycle = self._fetch_cycle(
                connection,
                """
                SELECT id, customer_id, cycle_number, status, valid_purchase_count,
                       total_amount, average_amount, started_at, completed_at
                FROM loyalty_cycles
                WHERE customer_id = ?
                ORDER BY cycle_number DESC
                LIMIT 1
                """,
                (customer_id,),
            )
            cycle_for_stickers = current_cycle or latest_cycle
            stickers = self._stickers_for_cycle(connection, cycle_for_stickers.id if cycle_for_stickers else None)
            completed_cycles = connection.execute(
                """
                SELECT COUNT(*)
                FROM loyalty_cycles
                WHERE customer_id = ? AND status = 'completed'
                """,
                (customer_id,),
            ).fetchone()[0]
            available_rewards = connection.execute(
                """
                SELECT COUNT(*)
                FROM rewards
                WHERE customer_id = ? AND status = 'available'
                """,
                (customer_id,),
            ).fetchone()[0]
            last_purchase_at = connection.execute(
                """
                SELECT MAX(purchased_at)
                FROM purchases
                WHERE customer_id = ? AND status = 'active'
                """,
                (customer_id,),
            ).fetchone()[0]

        return CustomerLoyaltySummary(
            current_cycle=current_cycle,
            latest_cycle=latest_cycle,
            completed_cycles=completed_cycles,
            available_rewards=available_rewards,
            last_purchase_at=last_purchase_at,
            stickers=stickers,
        )

    def cycles_for_customer(self, customer_id: int) -> list[CycleSummary]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, customer_id, cycle_number, status, valid_purchase_count,
                       total_amount, average_amount, started_at, completed_at
                FROM loyalty_cycles
                WHERE customer_id = ?
                ORDER BY cycle_number DESC
                """,
                (customer_id,),
            ).fetchall()
        return [self._cycle_from_row(row) for row in rows]

    def _stickers_for_cycle(
        self,
        connection: sqlite3.Connection,
        cycle_id: int | None,
    ) -> list[StickerSummary]:
        purchases = {}
        if cycle_id is not None:
            rows = connection.execute(
                """
                SELECT sticker_number, purchased_at, summary, total_amount
                FROM purchases
                WHERE cycle_id = ? AND status = 'active'
                ORDER BY sticker_number
                """,
                (cycle_id,),
            ).fetchall()
            purchases = {row[0]: row for row in rows}

        stickers: list[StickerSummary] = []
        for sticker_number in range(1, SETTINGS.stickers_per_cycle + 1):
            row = purchases.get(sticker_number)
            stickers.append(
                StickerSummary(
                    sticker_number=sticker_number,
                    purchased_at=row[1] if row else None,
                    summary=row[2] if row else None,
                    total_amount=money_from_db(row[3]) if row else None,
                )
            )
        return stickers

    def _fetch_cycle(self, connection: sqlite3.Connection, query: str, parameters: tuple) -> CycleSummary | None:
        row = connection.execute(query, parameters).fetchone()
        return self._cycle_from_row(row) if row else None

    @staticmethod
    def _cycle_from_row(row) -> CycleSummary:
        return CycleSummary(
            id=row[0],
            customer_id=row[1],
            cycle_number=row[2],
            status=row[3],
            valid_purchase_count=row[4],
            total_amount=money_from_db(row[5]),
            average_amount=money_from_db(row[6]),
            started_at=row[7],
            completed_at=row[8],
        )
