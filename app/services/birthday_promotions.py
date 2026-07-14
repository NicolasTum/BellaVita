from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.utils.dates import MONTH_NAMES


@dataclass(frozen=True)
class BirthdayPromotionCustomer:
    id: int
    first_name: str
    last_name: str
    birth_date: str
    phone: str | None
    email: str | None
    marketing_consent: bool
    last_purchase_at: str | None
    available_rewards: int

    @property
    def birthday_month(self) -> int:
        return int(self.birth_date[5:7])

    @property
    def birthday_day(self) -> int:
        return int(self.birth_date[8:10])

    @property
    def birthday_month_name(self) -> str:
        return MONTH_NAMES[self.birthday_month]


class BirthdayPromotionService:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def count_birthdays_for_month(self, month: int) -> int:
        return len(self.list_birthdays_for_month(month))

    def list_birthdays_for_month(self, month: int, search_text: str = "") -> list[BirthdayPromotionCustomer]:
        return [
            customer
            for customer in self._eligible_customers(search_text)
            if customer.birthday_month == month
        ]

    def customers_for_month(
        self,
        month: int,
        require_marketing_consent: bool = True,
        require_contact: bool = False,
    ) -> list[BirthdayPromotionCustomer]:
        return self.list_birthdays_for_month(month)

    def customers_with_birth_date(self) -> list[BirthdayPromotionCustomer]:
        return self._eligible_customers("")

    def customers_without_birth_date(self) -> list[int]:
        with sqlite3.connect(self._database_path) as connection:
            return [
                row[0]
                for row in connection.execute(
                    "SELECT id FROM customers WHERE birth_date IS NULL ORDER BY last_name, first_name"
                ).fetchall()
            ]

    def birthdays_today(self, today: date | None = None) -> list[BirthdayPromotionCustomer]:
        current = today or date.today()
        return [
            customer
            for customer in self._eligible_customers("")
            if (customer.birthday_month, customer.birthday_day) == (current.month, current.day)
        ]

    def birthdays_this_week(self, today: date | None = None) -> list[BirthdayPromotionCustomer]:
        current = today or date.today()
        days = {(current + timedelta(days=offset)).strftime("%m-%d") for offset in range(7)}
        return [
            customer
            for customer in self._eligible_customers("")
            if customer.birth_date[5:10] in days
        ]

    def birthdays_next_month(self, today: date | None = None) -> list[BirthdayPromotionCustomer]:
        current = today or date.today()
        month = 1 if current.month == 12 else current.month + 1
        return self.customers_for_month(month)

    def customers_for_month_range(self, start_month: int, end_month: int) -> list[BirthdayPromotionCustomer]:
        months = self._month_range(start_month, end_month)
        return [
            customer
            for customer in self._eligible_customers("")
            if customer.birthday_month in months
        ]

    def export_birthdays_for_month(self, month: int, destination: Path, search_text: str = "") -> Path:
        customers = self.list_birthdays_for_month(month, search_text=search_text)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Nombre",
                    "Apellido",
                    "Fecha de nacimiento",
                    "Día de cumpleaños",
                    "Mes de cumpleaños",
                    "Teléfono",
                    "Correo",
                    "Fecha de última compra",
                    "Premios disponibles",
                ]
            )
            for customer in customers:
                writer.writerow(
                    [
                        customer.first_name,
                        customer.last_name,
                        customer.birth_date,
                        f"{customer.birthday_day:02d}",
                        customer.birthday_month_name,
                        customer.phone or "",
                        customer.email or "",
                        customer.last_purchase_at or "",
                        customer.available_rewards,
                    ]
                )
        self._audit_export(month, len(customers), destination)
        return destination

    def export_month(self, month: int, destination: Path, require_marketing_consent: bool = True) -> Path:
        return self.export_birthdays_for_month(month, destination)

    def inconsistent_customers(self) -> list[int]:
        with sqlite3.connect(self._database_path) as connection:
            return [
                row[0]
                for row in connection.execute(
                    """
                    SELECT id
                    FROM customers
                    WHERE birth_date IS NOT NULL AND marketing_consent = 0
                    ORDER BY id
                    """
                ).fetchall()
            ]

    def _eligible_customers(self, search_text: str) -> list[BirthdayPromotionCustomer]:
        clauses = ["c.is_active = 1", "c.birth_date IS NOT NULL", "c.marketing_consent = 1"]
        parameters: list[str] = []
        cleaned = search_text.strip().lower()
        if cleaned:
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
            like = f"%{cleaned}%"
            parameters.extend([like, like, like, like, like])
        where = " AND ".join(clauses)
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    c.id, c.first_name, c.last_name, c.birth_date, c.phone, c.email,
                    c.marketing_consent,
                    (
                        SELECT MAX(purchased_at)
                        FROM purchases p
                        WHERE p.customer_id = c.id AND p.status = 'active'
                    ) AS last_purchase_at,
                    COALESCE((
                        SELECT COUNT(*)
                        FROM rewards r
                        WHERE r.customer_id = c.id AND r.status = 'available'
                    ), 0) AS available_rewards
                FROM customers c
                WHERE {where}
                ORDER BY CAST(strftime('%d', c.birth_date) AS INTEGER), c.last_name, c.first_name
                """,
                parameters,
            ).fetchall()
        return [BirthdayPromotionCustomer(*row[:6], bool(row[6]), row[7], row[8]) for row in rows]

    def _audit_export(self, month: int, count: int, destination: Path) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO audit_logs (action, entity, new_value, reason)
                VALUES ('BIRTHDAY_LIST_EXPORTED', 'birthday_promotions', ?, ?)
                """,
                (f"month={month};count={count}", f"Exported to {destination.name}"),
            )

    @staticmethod
    def _month_range(start_month: int, end_month: int) -> set[int]:
        if not 1 <= start_month <= 12 or not 1 <= end_month <= 12:
            raise ValueError("Los meses deben estar entre 1 y 12.")
        if start_month <= end_month:
            return set(range(start_month, end_month + 1))
        return set(range(start_month, 13)) | set(range(1, end_month + 1))
