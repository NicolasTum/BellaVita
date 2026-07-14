from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.utils.money import money_from_db


@dataclass(frozen=True)
class DashboardStats:
    purchases_today: int
    rewards_available: int
    rewards_available_value: Decimal
    rewards_used: int
    cycles_near_completion: int
    birthdays_this_month: int
    upcoming_birthdays: tuple[tuple[str, str, str | None, str | None, bool], ...]


class DashboardRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def stats(self) -> DashboardStats:
        with sqlite3.connect(self._database_path) as connection:
            purchases_today = connection.execute(
                "SELECT COUNT(*) FROM purchases WHERE date(purchased_at) = date(CURRENT_TIMESTAMP) AND status = 'active'"
            ).fetchone()[0]
            rewards_available = connection.execute(
                "SELECT COUNT(*) FROM rewards WHERE status = 'available'"
            ).fetchone()[0]
            rewards_available_value = connection.execute(
                "SELECT COALESCE(SUM(max_value), 0) FROM rewards WHERE status = 'available'"
            ).fetchone()[0]
            rewards_used = connection.execute(
                "SELECT COUNT(*) FROM rewards WHERE status = 'used'"
            ).fetchone()[0]
            cycles_near_completion = connection.execute(
                """
                SELECT COUNT(*)
                FROM loyalty_cycles
                WHERE status = 'in_progress' AND valid_purchase_count = target_purchase_count - 1
                """
            ).fetchone()[0]
            birthdays_this_month = connection.execute(
                """
                SELECT COUNT(*)
                FROM customers
                WHERE is_active = 1
                  AND birth_date IS NOT NULL
                  AND strftime('%m', birth_date) = strftime('%m', CURRENT_DATE)
                """
            ).fetchone()[0]
            birthday_rows = connection.execute(
                """
                SELECT first_name || ' ' || last_name, birth_date, phone, email, marketing_consent
                FROM customers
                WHERE is_active = 1
                  AND birth_date IS NOT NULL
                """
            ).fetchall()
            upcoming_birthdays = self._upcoming_birthdays(birthday_rows)
        return DashboardStats(
            purchases_today=purchases_today,
            rewards_available=rewards_available,
            rewards_available_value=money_from_db(rewards_available_value),
            rewards_used=rewards_used,
            cycles_near_completion=cycles_near_completion,
            birthdays_this_month=birthdays_this_month,
            upcoming_birthdays=upcoming_birthdays,
        )

    @staticmethod
    def _upcoming_birthdays(rows) -> tuple[tuple[str, str, str | None, str | None, bool], ...]:
        today = date.today()
        ordered = []
        for name, birth_date, phone, email, consent in rows:
            month = int(birth_date[5:7])
            day = int(birth_date[8:10])
            candidate = date(today.year, month, day)
            if candidate < today:
                candidate = date(today.year + 1, month, day)
            ordered.append((candidate, name, f"{day:02d}/{month:02d}", phone, email, bool(consent)))
        ordered.sort(key=lambda item: item[0])
        return tuple((name, day_month, phone, email, consent) for _, name, day_month, phone, email, consent in ordered[:5])
