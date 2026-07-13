from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.config.settings import SETTINGS
from app.utils.money import money_from_db, money_to_db, to_decimal


class PurchaseValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PurchaseItemInput:
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def subtotal(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class PurchaseInput:
    customer_id: int
    summary: str
    total_amount: Decimal
    notes: str | None
    items: tuple[PurchaseItemInput, ...]
    operation_id: str
    user_id: int | None = None


@dataclass(frozen=True)
class PurchaseResult:
    purchase_id: int
    customer_id: int
    cycle_id: int
    cycle_number: int
    sticker_number: int
    missing_count: int
    cycle_completed: bool
    reward_id: int | None
    reward_value: Decimal | None
    total_amount: Decimal
    cycle_total: Decimal
    cycle_average: Decimal


class PurchaseService:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def build_simple_purchase(
        self,
        customer_id: int,
        summary: str,
        total_amount: str,
        notes: str = "",
        operation_id: str | None = None,
    ) -> PurchaseInput:
        amount = to_decimal(total_amount)
        item = PurchaseItemInput(summary.strip(), Decimal("1"), amount)
        return self._build_purchase(
            customer_id=customer_id,
            summary=summary,
            total_amount=amount,
            notes=notes,
            items=(item,),
            operation_id=operation_id,
        )

    def build_detailed_purchase(
        self,
        customer_id: int,
        items: list[tuple[str, str, str]],
        notes: str = "",
        operation_id: str | None = None,
    ) -> PurchaseInput:
        built_items: list[PurchaseItemInput] = []
        for description, quantity, unit_price in items:
            item = PurchaseItemInput(
                description=description.strip(),
                quantity=to_decimal(quantity),
                unit_price=to_decimal(unit_price),
            )
            built_items.append(item)

        total = sum((item.subtotal for item in built_items), Decimal("0.00"))
        summary = ", ".join(item.description for item in built_items[:3])
        if len(built_items) > 3:
            summary += f" y {len(built_items) - 3} mas"
        return self._build_purchase(
            customer_id=customer_id,
            summary=summary,
            total_amount=total,
            notes=notes,
            items=tuple(built_items),
            operation_id=operation_id,
        )

    def register_purchase(self, purchase: PurchaseInput) -> PurchaseResult:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT id, customer_id, cycle_id, cycle_number, sticker_number, total_amount
                FROM purchases
                WHERE operation_id = ?
                """,
                (purchase.operation_id,),
            ).fetchone()
            if existing:
                cycle = self._cycle_by_id(connection, existing[2])
                reward = self._reward_for_cycle(connection, existing[2])
                return PurchaseResult(
                    purchase_id=existing[0],
                    customer_id=existing[1],
                    cycle_id=existing[2],
                    cycle_number=existing[3],
                    sticker_number=existing[4],
                    missing_count=max(0, SETTINGS.stickers_per_cycle - cycle["valid_purchase_count"]),
                    cycle_completed=cycle["status"] == "completed",
                    reward_id=reward[0] if reward else None,
                    reward_value=money_from_db(reward[1]) if reward else None,
                    total_amount=money_from_db(existing[5]),
                    cycle_total=money_from_db(cycle["total_amount"]),
                    cycle_average=money_from_db(cycle["average_amount"]),
                )

            customer = connection.execute(
                "SELECT id, first_name, last_name, is_active FROM customers WHERE id = ?",
                (purchase.customer_id,),
            ).fetchone()
            if not customer:
                raise PurchaseValidationError("Seleccioná un cliente válido.")
            if not bool(customer[3]):
                raise PurchaseValidationError("No se pueden registrar compras para clientes inactivos.")

            cycle = self._get_or_create_active_cycle(connection, purchase.customer_id)
            if cycle["valid_purchase_count"] >= SETTINGS.stickers_per_cycle:
                raise PurchaseValidationError("El ciclo ya tiene seis compras.")

            sticker_number = cycle["valid_purchase_count"] + 1
            cursor = connection.execute(
                """
                INSERT INTO purchases (
                    customer_id, cycle_id, cycle_number, sticker_number, purchased_at,
                    summary, total_amount, notes, registered_by_user_id, operation_id
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
                """,
                (
                    purchase.customer_id,
                    cycle["id"],
                    cycle["cycle_number"],
                    sticker_number,
                    purchase.summary,
                    money_to_db(purchase.total_amount),
                    purchase.notes,
                    purchase.user_id,
                    purchase.operation_id,
                ),
            )
            purchase_id = int(cursor.lastrowid)

            for item in purchase.items:
                connection.execute(
                    """
                    INSERT INTO purchase_items (purchase_id, description, quantity, unit_price, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        purchase_id,
                        item.description,
                        str(item.quantity),
                        money_to_db(item.unit_price),
                        money_to_db(item.subtotal),
                    ),
                )

            count, total = self._cycle_totals(connection, cycle["id"])
            partial_average = (total / Decimal(count)).quantize(Decimal("0.01")) if count else Decimal("0.00")
            cycle_completed = count == SETTINGS.stickers_per_cycle
            reward_id: int | None = None
            reward_value: Decimal | None = None

            connection.execute(
                """
                UPDATE loyalty_cycles
                SET valid_purchase_count = ?,
                    total_amount = ?,
                    average_amount = ?,
                    status = ?,
                    completed_at = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE completed_at END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    count,
                    money_to_db(total),
                    money_to_db(partial_average),
                    "completed" if cycle_completed else "in_progress",
                    1 if cycle_completed else 0,
                    cycle["id"],
                ),
            )

            self._audit(
                connection,
                purchase.user_id,
                "PURCHASE_CREATED",
                "purchases",
                purchase_id,
                f"customer_id={purchase.customer_id};cycle={cycle['cycle_number']};sticker={sticker_number};total={purchase.total_amount}",
            )

            if cycle_completed:
                existing_reward = self._reward_for_cycle(connection, cycle["id"])
                if existing_reward:
                    reward_id = existing_reward[0]
                    reward_value = money_from_db(existing_reward[1])
                else:
                    reward_value = partial_average
                    reward_cursor = connection.execute(
                        """
                        INSERT INTO rewards (
                            customer_id, cycle_id, earned_at, max_value, status, notes
                        )
                        VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'available', ?)
                        """,
                        (
                            purchase.customer_id,
                            cycle["id"],
                            money_to_db(reward_value),
                            f"Premio generado por ciclo {cycle['cycle_number']}",
                        ),
                    )
                    reward_id = int(reward_cursor.lastrowid)
                    self._audit(
                        connection,
                        purchase.user_id,
                        "CYCLE_COMPLETED",
                        "loyalty_cycles",
                        cycle["id"],
                        f"customer_id={purchase.customer_id};total={total};average={partial_average}",
                    )
                    self._audit(
                        connection,
                        purchase.user_id,
                        "REWARD_CREATED",
                        "rewards",
                        reward_id,
                        f"customer_id={purchase.customer_id};cycle_id={cycle['id']};max_value={reward_value}",
                    )

            return PurchaseResult(
                purchase_id=purchase_id,
                customer_id=purchase.customer_id,
                cycle_id=cycle["id"],
                cycle_number=cycle["cycle_number"],
                sticker_number=sticker_number,
                missing_count=max(0, SETTINGS.stickers_per_cycle - count),
                cycle_completed=cycle_completed,
                reward_id=reward_id,
                reward_value=reward_value,
                total_amount=purchase.total_amount,
                cycle_total=total,
                cycle_average=partial_average,
            )

    def _build_purchase(
        self,
        customer_id: int,
        summary: str,
        total_amount: Decimal,
        notes: str,
        items: tuple[PurchaseItemInput, ...],
        operation_id: str | None,
    ) -> PurchaseInput:
        cleaned_summary = summary.strip()
        if customer_id <= 0:
            raise PurchaseValidationError("Seleccioná un cliente.")
        if not cleaned_summary:
            raise PurchaseValidationError("La descripción es obligatoria.")
        if total_amount <= 0:
            raise PurchaseValidationError("El importe debe ser mayor que cero.")
        if not items:
            raise PurchaseValidationError("Agregá al menos un producto.")
        for item in items:
            if not item.description:
                raise PurchaseValidationError("La descripción de cada producto es obligatoria.")
            if item.quantity <= 0:
                raise PurchaseValidationError("La cantidad debe ser mayor que cero.")
            if item.unit_price < 0:
                raise PurchaseValidationError("El precio no puede ser negativo.")
        return PurchaseInput(
            customer_id=customer_id,
            summary=cleaned_summary,
            total_amount=total_amount,
            notes=notes.strip() or None,
            items=items,
            operation_id=operation_id or str(uuid4()),
        )

    def _get_or_create_active_cycle(self, connection: sqlite3.Connection, customer_id: int) -> dict:
        row = connection.execute(
            """
            SELECT id, customer_id, cycle_number, status, valid_purchase_count, total_amount, average_amount
            FROM loyalty_cycles
            WHERE customer_id = ? AND status = 'in_progress'
            ORDER BY cycle_number DESC
            LIMIT 1
            """,
            (customer_id,),
        ).fetchone()
        if row:
            return self._cycle_dict(row)

        next_number = connection.execute(
            "SELECT COALESCE(MAX(cycle_number), 0) + 1 FROM loyalty_cycles WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()[0]
        cursor = connection.execute(
            """
            INSERT INTO loyalty_cycles (customer_id, cycle_number, status)
            VALUES (?, ?, 'in_progress')
            """,
            (customer_id, next_number),
        )
        cycle_id = int(cursor.lastrowid)
        self._audit(
            connection,
            None,
            "CYCLE_CREATED",
            "loyalty_cycles",
            cycle_id,
            f"customer_id={customer_id};cycle={next_number}",
        )
        return {
            "id": cycle_id,
            "customer_id": customer_id,
            "cycle_number": next_number,
            "status": "in_progress",
            "valid_purchase_count": 0,
            "total_amount": "0.00",
            "average_amount": "0.00",
        }

    def _cycle_by_id(self, connection: sqlite3.Connection, cycle_id: int) -> dict:
        row = connection.execute(
            """
            SELECT id, customer_id, cycle_number, status, valid_purchase_count, total_amount, average_amount
            FROM loyalty_cycles
            WHERE id = ?
            """,
            (cycle_id,),
        ).fetchone()
        return self._cycle_dict(row)

    @staticmethod
    def _cycle_dict(row) -> dict:
        return {
            "id": row[0],
            "customer_id": row[1],
            "cycle_number": row[2],
            "status": row[3],
            "valid_purchase_count": row[4],
            "total_amount": row[5],
            "average_amount": row[6],
        }

    def _cycle_totals(self, connection: sqlite3.Connection, cycle_id: int) -> tuple[int, Decimal]:
        rows = connection.execute(
            "SELECT total_amount FROM purchases WHERE cycle_id = ? AND status = 'active'",
            (cycle_id,),
        ).fetchall()
        total = sum((money_from_db(row[0]) for row in rows), Decimal("0.00"))
        return len(rows), total

    def _reward_for_cycle(self, connection: sqlite3.Connection, cycle_id: int):
        return connection.execute(
            "SELECT id, max_value FROM rewards WHERE cycle_id = ?",
            (cycle_id,),
        ).fetchone()

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
