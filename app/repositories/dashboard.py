from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DashboardStats:
    purchases_today: int
    rewards_available: int
    rewards_used: int
    cycles_near_completion: int


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
        return DashboardStats(
            purchases_today=purchases_today,
            rewards_available=rewards_available,
            rewards_used=rewards_used,
            cycles_near_completion=cycles_near_completion,
        )
