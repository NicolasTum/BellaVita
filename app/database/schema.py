from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'seller')),
    must_change_password INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    birth_date TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    marketing_consent INTEGER NOT NULL DEFAULT 0,
    marketing_consent_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (phone IS NOT NULL AND length(trim(phone)) > 0)
        OR (email IS NOT NULL AND length(trim(email)) > 0)
    )
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(last_name, first_name);

CREATE TABLE IF NOT EXISTS loyalty_cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    cycle_number INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'adjusted', 'closed')),
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target_purchase_count INTEGER NOT NULL DEFAULT 6,
    valid_purchase_count INTEGER NOT NULL DEFAULT 0,
    total_amount NUMERIC NOT NULL DEFAULT 0,
    average_amount NUMERIC NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, cycle_number)
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    cycle_id INTEGER NOT NULL REFERENCES loyalty_cycles(id),
    cycle_number INTEGER NOT NULL,
    sticker_number INTEGER NOT NULL CHECK (sticker_number >= 1),
    purchased_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    total_amount NUMERIC NOT NULL CHECK (total_amount > 0),
    notes TEXT,
    registered_by_user_id INTEGER REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'voided')),
    operation_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cycle_id, sticker_number)
);

CREATE TABLE IF NOT EXISTS purchase_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id),
    description TEXT NOT NULL,
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
    subtotal NUMERIC NOT NULL CHECK (subtotal >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    cycle_id INTEGER NOT NULL REFERENCES loyalty_cycles(id),
    earned_at TEXT NOT NULL,
    max_value NUMERIC NOT NULL CHECK (max_value >= 0),
    status TEXT NOT NULL CHECK (status IN ('available', 'used', 'expired', 'cancelled')),
    used_at TEXT,
    delivered_item_description TEXT,
    delivered_item_price NUMERIC,
    value_difference NUMERIC,
    notes TEXT,
    delivered_by_user_id INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rewards_cycle_id ON rewards(cycle_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS backup_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    path TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    reason TEXT,
    error TEXT,
    restored_from TEXT
);
"""


def initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute("PRAGMA foreign_keys = ON;")
        _apply_compatible_upgrades(connection)
        _seed_default_settings(connection)


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


def _apply_compatible_upgrades(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = OFF;")
    _rebuild_purchases_if_legacy_sticker_check(connection)
    _rebuild_purchase_items_if_legacy_fk(connection)
    connection.execute("PRAGMA foreign_keys = ON;")
    cycle_columns = _column_names(connection, "loyalty_cycles")
    if "started_at" not in cycle_columns:
        connection.execute(
            "ALTER TABLE loyalty_cycles ADD COLUMN started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )
    if "valid_purchase_count" not in cycle_columns:
        connection.execute(
            "ALTER TABLE loyalty_cycles ADD COLUMN valid_purchase_count INTEGER NOT NULL DEFAULT 0"
        )
    if "target_purchase_count" not in cycle_columns:
        connection.execute(
            "ALTER TABLE loyalty_cycles ADD COLUMN target_purchase_count INTEGER NOT NULL DEFAULT 6"
        )

    purchase_columns = _column_names(connection, "purchases")
    if "operation_id" not in purchase_columns:
        connection.execute("ALTER TABLE purchases ADD COLUMN operation_id TEXT")

    customer_columns = _column_names(connection, "customers")
    if "birth_date" not in customer_columns:
        connection.execute("ALTER TABLE customers ADD COLUMN birth_date TEXT")
        connection.execute(
            """
            INSERT INTO audit_logs (action, entity, new_value, reason)
            VALUES ('MIGRATION_APPLIED', 'customers', 'birth_date', 'Added optional customer birth date')
            """
        )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_operation_id
        ON purchases(operation_id)
        WHERE operation_id IS NOT NULL
        """
    )
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_rewards_cycle_id ON rewards(cycle_id)")
    backup_columns = _column_names(connection, "backup_logs")
    if "reason" not in backup_columns:
        connection.execute("ALTER TABLE backup_logs ADD COLUMN reason TEXT")
    if "error" not in backup_columns:
        connection.execute("ALTER TABLE backup_logs ADD COLUMN error TEXT")
    if "restored_from" not in backup_columns:
        connection.execute("ALTER TABLE backup_logs ADD COLUMN restored_from TEXT")


def _rebuild_purchases_if_legacy_sticker_check(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'purchases'"
    ).fetchone()
    legacy_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'purchases_legacy'"
    ).fetchone()
    if legacy_exists and row and "sticker_number BETWEEN 1 AND 6" not in row[0]:
        return
    if not row or "sticker_number BETWEEN 1 AND 6" not in row[0]:
        return

    connection.execute("ALTER TABLE purchases RENAME TO purchases_legacy")
    connection.execute(
        """
        CREATE TABLE purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            cycle_id INTEGER NOT NULL REFERENCES loyalty_cycles(id),
            cycle_number INTEGER NOT NULL,
            sticker_number INTEGER NOT NULL CHECK (sticker_number >= 1),
            purchased_at TEXT NOT NULL,
            summary TEXT NOT NULL,
            total_amount NUMERIC NOT NULL CHECK (total_amount > 0),
            notes TEXT,
            registered_by_user_id INTEGER REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'voided')),
            operation_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cycle_id, sticker_number)
        )
        """
    )
    legacy_columns = _column_names(connection, "purchases_legacy")
    operation_expr = "operation_id" if "operation_id" in legacy_columns else "NULL"
    connection.execute(
        f"""
        INSERT INTO purchases (
            id, customer_id, cycle_id, cycle_number, sticker_number, purchased_at,
            summary, total_amount, notes, registered_by_user_id, status,
            operation_id, created_at, updated_at
        )
        SELECT id, customer_id, cycle_id, cycle_number, sticker_number, purchased_at,
               summary, total_amount, notes, registered_by_user_id, status,
               {operation_expr}, created_at, updated_at
        FROM purchases_legacy
        """
    )


def _rebuild_purchase_items_if_legacy_fk(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'purchase_items'"
    ).fetchone()
    if not row or "purchases_legacy" not in row[0]:
        _drop_legacy_purchases_if_safe(connection)
        return

    connection.execute("ALTER TABLE purchase_items RENAME TO purchase_items_legacy")
    connection.execute(
        """
        CREATE TABLE purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL REFERENCES purchases(id),
            description TEXT NOT NULL,
            quantity NUMERIC NOT NULL CHECK (quantity > 0),
            unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
            subtotal NUMERIC NOT NULL CHECK (subtotal >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO purchase_items (
            id, purchase_id, description, quantity, unit_price, subtotal, created_at
        )
        SELECT id, purchase_id, description, quantity, unit_price, subtotal, created_at
        FROM purchase_items_legacy
        """
    )
    connection.execute("DROP TABLE purchase_items_legacy")
    _drop_legacy_purchases_if_safe(connection)


def _drop_legacy_purchases_if_safe(connection: sqlite3.Connection) -> None:
    legacy_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'purchases_legacy'"
    ).fetchone()
    if legacy_exists:
        connection.execute("DROP TABLE purchases_legacy")


DEFAULT_APP_SETTINGS = {
    "store_name": "Club de Compras",
    "store_phone": "",
    "store_email": "",
    "store_address": "",
    "promotion_name": "Club de Compras",
    "promotion_description": "Cada ciclo completo genera un premio segun el promedio de compras.",
    "loyalty_target_purchase_count": "6",
    "loyalty_active": "1",
    "allow_new_cycle_with_pending_reward": "1",
    "promotion_sender_name": "",
    "promotion_sender_email": "",
    "promotion_reply_to_email": "",
    "promotion_default_subject": "Promociones",
    "promotion_default_signature": "",
    "promotion_email_status": "not_configured",
    "currency_code": "UYU",
    "currency_symbol": "$",
    "promotion_legal_text": "",
    "marketing_consent_required": "0",
    "backup_folder_path": "",
}


def _seed_default_settings(connection: sqlite3.Connection) -> None:
    for key, value in DEFAULT_APP_SETTINGS.items():
        connection.execute(
            """
            INSERT OR IGNORE INTO app_settings (key, value)
            VALUES (?, ?)
            """,
            (key, value),
        )
