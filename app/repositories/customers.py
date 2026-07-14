from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CustomerCreate:
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    birth_date: str | None = None
    notes: str | None = None
    marketing_consent: bool = False


@dataclass(frozen=True)
class CustomerDuplicate:
    id: int
    first_name: str
    last_name: str
    phone: str | None
    email: str | None
    reason: str


@dataclass(frozen=True)
class CustomerRecord:
    id: int
    first_name: str
    last_name: str
    phone: str | None
    email: str | None
    birth_date: str | None
    notes: str | None
    is_active: bool
    marketing_consent: bool
    created_at: str
    current_stickers: int = 0
    available_rewards: int = 0
    last_purchase_at: str | None = None
    current_cycle_total: str = "0.00"
    current_cycle_average: str = "0.00"
    current_cycle_target: int = 6
    completed_cycles: int = 0

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class CustomerRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(self, customer: CustomerCreate) -> int:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            cursor = connection.execute(
                """
                INSERT INTO customers (
                    first_name,
                    last_name,
                    phone,
                    email,
                    birth_date,
                    notes,
                    marketing_consent,
                    marketing_consent_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END)
                """,
                (
                    customer.first_name,
                    customer.last_name,
                    customer.phone,
                    customer.email,
                    customer.birth_date,
                    customer.notes,
                    1 if customer.marketing_consent else 0,
                    1 if customer.marketing_consent else 0,
                ),
            )
            customer_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO audit_logs (action, entity, entity_id, new_value)
                VALUES ('customer_created', 'customers', ?, ?)
                """,
                (customer_id, f"{customer.first_name} {customer.last_name}"),
            )
            return customer_id

    def update(self, customer_id: int, customer: CustomerCreate) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute(
                """
                UPDATE customers
                SET first_name = ?,
                    last_name = ?,
                    phone = ?,
                    email = ?,
                    birth_date = ?,
                    notes = ?,
                    marketing_consent = ?,
                    marketing_consent_at = CASE
                        WHEN ? = 1 AND marketing_consent_at IS NULL THEN CURRENT_TIMESTAMP
                        WHEN ? = 0 THEN NULL
                        ELSE marketing_consent_at
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    customer.first_name,
                    customer.last_name,
                    customer.phone,
                    customer.email,
                    customer.birth_date,
                    customer.notes,
                    1 if customer.marketing_consent else 0,
                    1 if customer.marketing_consent else 0,
                    1 if customer.marketing_consent else 0,
                    customer_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO audit_logs (action, entity, entity_id, new_value)
                VALUES ('customer_updated', 'customers', ?, ?)
                """,
                (customer_id, f"{customer.first_name} {customer.last_name}"),
            )

    def set_active(self, customer_id: int, is_active: bool) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute(
                """
                UPDATE customers
                SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (1 if is_active else 0, customer_id),
            )
            connection.execute(
                """
                INSERT INTO audit_logs (action, entity, entity_id, new_value)
                VALUES (?, 'customers', ?, ?)
                """,
                (
                    "customer_activated" if is_active else "customer_deactivated",
                    customer_id,
                    "active" if is_active else "inactive",
                ),
            )

    def get(self, customer_id: int) -> CustomerRecord | None:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    c.id,
                    c.first_name,
                    c.last_name,
                    c.phone,
                    c.email,
                    c.birth_date,
                    c.notes,
                    c.is_active,
                    c.marketing_consent,
                    c.created_at,
                    COALESCE((
                        SELECT COUNT(*)
                        FROM purchases p
                        JOIN loyalty_cycles lc ON lc.id = p.cycle_id
                        WHERE p.customer_id = c.id
                          AND p.status = 'active'
                          AND lc.status = 'in_progress'
                    ), 0) AS current_stickers,
                    COALESCE((
                        SELECT COUNT(*)
                        FROM rewards r
                        WHERE r.customer_id = c.id
                          AND r.status = 'available'
                    ), 0) AS available_rewards,
                    (
                        SELECT MAX(purchased_at)
                        FROM purchases p
                        WHERE p.customer_id = c.id
                          AND p.status = 'active'
                    ) AS last_purchase_at,
                    COALESCE((
                        SELECT lc.total_amount
                        FROM loyalty_cycles lc
                        WHERE lc.customer_id = c.id AND lc.status = 'in_progress'
                        ORDER BY lc.cycle_number DESC
                        LIMIT 1
                    ), 0) AS current_cycle_total,
                    COALESCE((
                        SELECT lc.average_amount
                        FROM loyalty_cycles lc
                        WHERE lc.customer_id = c.id AND lc.status = 'in_progress'
                        ORDER BY lc.cycle_number DESC
                        LIMIT 1
                    ), 0) AS current_cycle_average,
                    COALESCE((
                        SELECT lc.target_purchase_count
                        FROM loyalty_cycles lc
                        WHERE lc.customer_id = c.id AND lc.status = 'in_progress'
                        ORDER BY lc.cycle_number DESC
                        LIMIT 1
                    ), 6) AS current_cycle_target,
                    COALESCE((
                        SELECT COUNT(*)
                        FROM loyalty_cycles lc
                        WHERE lc.customer_id = c.id AND lc.status = 'completed'
                    ), 0) AS completed_cycles
                FROM customers c
                WHERE c.id = ?
                """,
                (customer_id,),
            ).fetchone()
        return self._record_from_row(row) if row else None

    def search(self, term: str = "") -> list[CustomerRecord]:
        cleaned = term.strip()
        parameters: list[str] = []
        where = ""
        if cleaned:
            like = f"%{cleaned.lower()}%"
            where = """
                WHERE lower(c.first_name) LIKE ?
                   OR lower(c.last_name) LIKE ?
                   OR lower(c.first_name || ' ' || c.last_name) LIKE ?
                   OR lower(COALESCE(c.phone, '')) LIKE ?
                   OR lower(COALESCE(c.email, '')) LIKE ?
                   OR CAST(c.id AS TEXT) LIKE ?
            """
            parameters = [like, like, like, like, like, f"%{cleaned}%"]

        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    c.id,
                    c.first_name,
                    c.last_name,
                    c.phone,
                    c.email,
                    c.birth_date,
                    c.notes,
                    c.is_active,
                    c.marketing_consent,
                    c.created_at,
                    COALESCE(active_cycle.stickers, 0) AS current_stickers,
                    COALESCE(available_rewards.count, 0) AS available_rewards,
                    last_purchase.last_purchase_at,
                    COALESCE(active_cycle.total_amount, 0) AS current_cycle_total,
                    COALESCE(active_cycle.average_amount, 0) AS current_cycle_average,
                    COALESCE(active_cycle.target_purchase_count, 6) AS current_cycle_target,
                    COALESCE(completed_cycles.count, 0) AS completed_cycles
                FROM customers c
                LEFT JOIN (
                    SELECT p.customer_id, COUNT(*) AS stickers, lc.total_amount, lc.average_amount,
                           lc.target_purchase_count
                    FROM purchases p
                    JOIN loyalty_cycles lc ON lc.id = p.cycle_id
                    WHERE p.status = 'active' AND lc.status = 'in_progress'
                    GROUP BY p.customer_id
                ) active_cycle ON active_cycle.customer_id = c.id
                LEFT JOIN (
                    SELECT customer_id, COUNT(*) AS count
                    FROM rewards
                    WHERE status = 'available'
                    GROUP BY customer_id
                ) available_rewards ON available_rewards.customer_id = c.id
                LEFT JOIN (
                    SELECT customer_id, MAX(purchased_at) AS last_purchase_at
                    FROM purchases
                    WHERE status = 'active'
                    GROUP BY customer_id
                ) last_purchase ON last_purchase.customer_id = c.id
                LEFT JOIN (
                    SELECT customer_id, COUNT(*) AS count
                    FROM loyalty_cycles
                    WHERE status = 'completed'
                    GROUP BY customer_id
                ) completed_cycles ON completed_cycles.customer_id = c.id
                {where}
                ORDER BY c.is_active DESC, c.last_name, c.first_name
                LIMIT 100
                """,
                parameters,
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def find_possible_duplicates(self, customer: CustomerCreate) -> list[CustomerDuplicate]:
        clauses: list[str] = []
        parameters: list[str] = []

        if customer.phone:
            clauses.append("(phone IS NOT NULL AND lower(trim(phone)) = lower(trim(?)))")
            parameters.append(customer.phone)
        if customer.email:
            clauses.append("(email IS NOT NULL AND lower(trim(email)) = lower(trim(?)))")
            parameters.append(customer.email)

        clauses.append("(lower(trim(first_name)) = lower(trim(?)) AND lower(trim(last_name)) = lower(trim(?)))")
        parameters.extend([customer.first_name, customer.last_name])

        query = f"""
            SELECT id, first_name, last_name, phone, email
            FROM customers
            WHERE is_active = 1 AND ({' OR '.join(clauses)})
            ORDER BY last_name, first_name
            LIMIT 10
        """

        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(query, parameters).fetchall()

        duplicates: list[CustomerDuplicate] = []
        for row in rows:
            reason = "nombre y apellido"
            if customer.phone and row[3] and row[3].strip().lower() == customer.phone.strip().lower():
                reason = "telefono"
            elif customer.email and row[4] and row[4].strip().lower() == customer.email.strip().lower():
                reason = "correo"
            duplicates.append(CustomerDuplicate(*row, reason=reason))
        return duplicates

    @staticmethod
    def _record_from_row(row) -> CustomerRecord:
        return CustomerRecord(
            id=row[0],
            first_name=row[1],
            last_name=row[2],
            phone=row[3],
            email=row[4],
            birth_date=row[5],
            notes=row[6],
            is_active=bool(row[7]),
            marketing_consent=bool(row[8]),
            created_at=row[9],
            current_stickers=row[10],
            available_rewards=row[11],
            last_purchase_at=row[12],
            current_cycle_total=str(row[13]),
            current_cycle_average=str(row[14]),
            current_cycle_target=row[15],
            completed_cycles=row[16],
        )
