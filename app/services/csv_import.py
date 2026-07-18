from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from app.repositories.customers import CustomerCreate, CustomerRecord
from app.services.customers import CustomerService, CustomerValidationError
from app.services.purchases import PurchaseService, PurchaseValidationError
from app.services.settings import CurrentUser, DEFAULT_ADMIN_USER, SettingsService
from app.utils.paths import export_dir


CSV_IMPORT_HEADERS = [
    "Nombre",
    "Apellido",
    "Telefono",
    "Correo",
    "Fecha_Nacimiento",
    "Consentimiento_Promociones",
    "Producto_1",
    "Monto_1",
    "Producto_2",
    "Monto_2",
    "Producto_3",
    "Monto_3",
    "Producto_4",
    "Monto_4",
    "Producto_5",
    "Monto_5",
    "Producto_6",
    "Monto_6",
    "Observaciones",
]


class CsvImportError(ValueError):
    pass


@dataclass(frozen=True)
class ImportPurchasePreview:
    index: int
    product: str
    amount: Decimal


@dataclass(frozen=True)
class ImportRowPreview:
    row_number: int
    first_name: str
    last_name: str
    phone: str
    normalized_phone: str
    email: str
    birth_date: str | None
    marketing_consent: bool
    notes: str
    purchases: tuple[ImportPurchasePreview, ...]
    total_amount: Decimal
    status: str
    messages: tuple[str, ...]
    existing_customer_id: int | None = None

    @property
    def is_valid(self) -> bool:
        return self.status != "Error"


@dataclass(frozen=True)
class ImportPreview:
    file_name: str
    file_hash: str
    rows: tuple[ImportRowPreview, ...]
    duplicate_batch_message: str | None = None

    @property
    def total_rows(self) -> int:
        return len(self.rows)

    @property
    def error_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "Error")


@dataclass(frozen=True)
class ImportRowResult:
    row_number: int
    status: str
    customer_name: str
    message: str
    customer_id: int | None
    purchases_created: int = 0


@dataclass(frozen=True)
class ImportResult:
    batch_id: int | None
    total_rows: int
    customers_created: int
    customers_updated: int
    rows_skipped: int
    rows_error: int
    purchases_created: int
    cycles_completed: int
    rewards_created: int
    row_results: tuple[ImportRowResult, ...]


class CsvImportService:
    def __init__(self, database_path: Path, current_user: CurrentUser = DEFAULT_ADMIN_USER) -> None:
        self._database_path = database_path
        self._current_user = current_user
        self._customer_service = CustomerService(database_path)
        self._settings_service = SettingsService(database_path, current_user)
        self._purchase_service = PurchaseService(database_path, self._settings_service)

    def require_admin(self) -> None:
        if not self._current_user.is_admin:
            raise CsvImportError("Solo un administrador puede importar clientes.")

    def template_headers(self) -> list[str]:
        return list(CSV_IMPORT_HEADERS)

    def write_template(self, destination: Path | None = None) -> tuple[Path, Path]:
        self.require_admin()
        target_dir = destination or export_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        csv_path = target_dir / "Plantilla_Importacion_Clientes_BellaVita.csv"
        instructions_path = target_dir / "Instrucciones_Importacion_Clientes.txt"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(CSV_IMPORT_HEADERS)
        instructions_path.write_text(
            "Cada fila representa un cliente. Nombre y Telefono son obligatorios.\n"
            "Puede cargar hasta seis compras historicas usando Producto_X y Monto_X.\n"
            "Consentimiento_Promociones admite SI, SÍ, TRUE, 1, NO, FALSE, 0 o vacio.\n"
            "Guarde el archivo como CSV UTF-8 antes de importarlo.\n",
            encoding="utf-8",
        )
        return csv_path, instructions_path

    def analyze_file(self, path: Path) -> ImportPreview:
        self.require_admin()
        content = path.read_bytes()
        return self.analyze_bytes(content, path.name)

    def analyze_bytes(self, content: bytes, file_name: str = "importacion.csv") -> ImportPreview:
        self.require_admin()
        file_hash = hashlib.sha256(content).hexdigest()
        duplicate = self._duplicate_batch_message(file_hash)
        text = content.decode("utf-8-sig")
        dialect = self._detect_dialect(text)
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if reader.fieldnames is None:
            raise CsvImportError("El archivo CSV no tiene encabezados.")
        missing = [header for header in CSV_IMPORT_HEADERS if header not in reader.fieldnames]
        if missing:
            raise CsvImportError(f"Faltan columnas obligatorias de plantilla: {', '.join(missing)}")

        rows = []
        existing_by_phone = self._customers_by_normalized_phone()
        for row_number, raw_row in enumerate(reader, start=2):
            rows.append(self._preview_row(row_number, raw_row, existing_by_phone))
        return ImportPreview(file_name, file_hash, tuple(rows), duplicate)

    def import_preview(
        self,
        preview: ImportPreview,
        existing_behavior: str = "update_empty_and_add_purchases",
        mode: str = "partial",
        allow_reimport: bool = False,
    ) -> ImportResult:
        self.require_admin()
        if preview.duplicate_batch_message and not allow_reimport:
            rows = tuple(
                ImportRowResult(row.row_number, "OMITIDO", self._row_name(row), preview.duplicate_batch_message, row.existing_customer_id)
                for row in preview.rows
            )
            return ImportResult(None, preview.total_rows, 0, 0, preview.total_rows, 0, 0, 0, 0, rows)
        if mode == "all_or_nothing" and preview.error_count:
            rows = tuple(
                ImportRowResult(row.row_number, "ERROR" if row.status == "Error" else "OMITIDO", self._row_name(row), "; ".join(row.messages) or "Importación cancelada por errores.", row.existing_customer_id)
                for row in preview.rows
            )
            return ImportResult(None, preview.total_rows, 0, 0, preview.total_rows - preview.error_count, preview.error_count, 0, 0, 0, rows)

        batch_id = self._start_batch(preview)
        totals = {
            "customers_created": 0,
            "customers_updated": 0,
            "rows_skipped": 0,
            "rows_error": 0,
            "purchases_created": 0,
            "cycles_completed": 0,
            "rewards_created": 0,
        }
        row_results: list[ImportRowResult] = []
        for row in preview.rows:
            if row.status == "Error":
                totals["rows_error"] += 1
                result = ImportRowResult(row.row_number, "ERROR", self._row_name(row), "; ".join(row.messages), row.existing_customer_id)
                row_results.append(result)
                self._record_row(batch_id, result)
                continue
            result, counters = self._import_row(batch_id, preview.file_hash, row, existing_behavior)
            row_results.append(result)
            for key, value in counters.items():
                totals[key] += value
            self._record_row(batch_id, result)
        self._complete_batch(batch_id, totals)
        self._audit("CSV_IMPORT_COMPLETED", batch_id, f"rows={preview.total_rows};purchases={totals['purchases_created']}")
        return ImportResult(
            batch_id,
            preview.total_rows,
            totals["customers_created"],
            totals["customers_updated"],
            totals["rows_skipped"],
            totals["rows_error"],
            totals["purchases_created"],
            totals["cycles_completed"],
            totals["rewards_created"],
            tuple(row_results),
        )

    def write_result_report(self, result: ImportResult, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Fila", "Resultado", "Cliente", "Mensaje", "ID"])
            for row in result.row_results:
                writer.writerow([row.row_number, row.status, row.customer_name, row.message, row.customer_id or ""])
        return destination

    def _preview_row(
        self,
        row_number: int,
        raw_row: dict[str, str],
        existing_by_phone: dict[str, CustomerRecord],
    ) -> ImportRowPreview:
        messages: list[str] = []
        first_name = self._text(raw_row.get("Nombre"))
        last_name = self._text(raw_row.get("Apellido"))
        phone = self._text(raw_row.get("Telefono"))
        normalized_phone = normalize_phone(phone)
        email = self._text(raw_row.get("Correo"))
        birth_raw = self._text(raw_row.get("Fecha_Nacimiento"))
        notes = self._text(raw_row.get("Observaciones"))
        consent = parse_consent(raw_row.get("Consentimiento_Promociones"))
        birth_date = None
        purchases: list[ImportPurchasePreview] = []

        if not first_name:
            messages.append("Nombre vacío.")
        if not phone:
            messages.append("Teléfono vacío.")
        if email and "@" not in email:
            messages.append("Correo inválido.")
        if birth_raw:
            try:
                birth_date = parse_birth_date(birth_raw)
            except CsvImportError as exc:
                messages.append(str(exc))
        for index in range(1, 7):
            product = self._text(raw_row.get(f"Producto_{index}"))
            amount_raw = self._text(raw_row.get(f"Monto_{index}"))
            if product and not amount_raw:
                messages.append(f"Producto_{index} informado sin Monto_{index}.")
            elif amount_raw and not product:
                messages.append(f"Monto_{index} informado sin Producto_{index}.")
            elif product and amount_raw:
                try:
                    amount = parse_money(amount_raw)
                except CsvImportError as exc:
                    messages.append(f"Monto_{index}: {exc}")
                else:
                    if amount <= 0:
                        messages.append(f"Monto_{index} debe ser mayor que cero.")
                    else:
                        purchases.append(ImportPurchasePreview(index, product, amount))
        existing = existing_by_phone.get(normalized_phone) if normalized_phone else None
        status = "Error" if messages else ("Cliente existente" if existing else "Listo para importar")
        if existing and not messages:
            conflict_messages = self._conflicts(existing, email, last_name, birth_date, notes)
            if conflict_messages:
                status = "Advertencia"
                messages.extend(conflict_messages)
        return ImportRowPreview(
            row_number,
            first_name,
            last_name,
            phone,
            normalized_phone,
            email,
            birth_date,
            consent,
            notes,
            tuple(purchases),
            sum((purchase.amount for purchase in purchases), Decimal("0.00")),
            status,
            tuple(messages),
            existing.id if existing else None,
        )

    def _import_row(
        self,
        batch_id: int,
        file_hash: str,
        row: ImportRowPreview,
        existing_behavior: str,
    ) -> tuple[ImportRowResult, dict[str, int]]:
        counters = {
            "customers_created": 0,
            "customers_updated": 0,
            "rows_skipped": 0,
            "rows_error": 0,
            "purchases_created": 0,
            "cycles_completed": 0,
            "rewards_created": 0,
        }
        if row.existing_customer_id and existing_behavior == "skip_existing":
            counters["rows_skipped"] = 1
            return ImportRowResult(row.row_number, "OMITIDO", self._row_name(row), "Cliente existente omitido.", row.existing_customer_id), counters

        try:
            customer_id, created, updated = self._upsert_customer(row, existing_behavior)
            counters["customers_created"] = 1 if created else 0
            counters["customers_updated"] = 1 if updated else 0
            purchase_results = []
            for purchase in row.purchases:
                operation_id = f"csv:{file_hash}:{row.row_number}:{purchase.index}"
                operation_existed = self._purchase_operation_exists(operation_id)
                purchase_input = self._purchase_service.build_simple_purchase(
                    customer_id,
                    purchase.product,
                    str(purchase.amount),
                    notes="Compra histórica importada por CSV.",
                    operation_id=operation_id,
                )
                result = self._purchase_service.register_purchase(purchase_input)
                if not operation_existed:
                    purchase_results.append(result)
                    self._audit("PURCHASE_IMPORTED_FROM_CSV", result.purchase_id, f"batch={batch_id};row={row.row_number}")
                    if result.cycle_completed:
                        self._audit("CYCLE_COMPLETED_FROM_CSV", result.cycle_id, f"batch={batch_id};row={row.row_number}")
                        counters["cycles_completed"] += 1
                    if result.reward_id:
                        self._audit("REWARD_CREATED_FROM_CSV", result.reward_id, f"batch={batch_id};row={row.row_number}")
                        counters["rewards_created"] += 1
            counters["purchases_created"] = len(purchase_results)
            message = f"Cliente {'creado' if created else 'actualizado' if updated else 'existente'} con {len(purchase_results)} compras."
            return ImportRowResult(row.row_number, "IMPORTADO", self._row_name(row), message, customer_id, len(purchase_results)), counters
        except (CustomerValidationError, PurchaseValidationError, sqlite3.Error, CsvImportError) as exc:
            counters["rows_error"] = 1
            return ImportRowResult(row.row_number, "ERROR", self._row_name(row), str(exc), row.existing_customer_id), counters

    def _upsert_customer(self, row: ImportRowPreview, behavior: str) -> tuple[int, bool, bool]:
        if row.existing_customer_id is None:
            customer = self._customer_service.build_customer(
                row.first_name,
                row.last_name,
                row.phone,
                row.email,
                row.notes,
                row.marketing_consent,
                row.birth_date or "",
            )
            customer_id = self._customer_service.create_customer(customer).customer_id
            self._audit("CUSTOMER_IMPORTED", customer_id, f"row={row.row_number}")
            return customer_id, True, False
        existing = self._customer_service.get_customer(row.existing_customer_id)
        if existing is None:
            raise CsvImportError("Cliente existente no encontrado.")
        if behavior == "add_purchases_only":
            return existing.id, False, False
        changed = False
        last_name = existing.last_name or row.last_name
        email = existing.email or row.email
        birth_date = existing.birth_date or row.birth_date
        notes = existing.notes or row.notes
        marketing_consent = existing.marketing_consent or row.marketing_consent
        changed = any(
            [
                last_name != existing.last_name,
                email != existing.email,
                birth_date != existing.birth_date,
                notes != existing.notes,
                marketing_consent != existing.marketing_consent,
            ]
        )
        if changed:
            customer = self._customer_service.build_customer(
                existing.first_name,
                last_name,
                existing.phone or row.phone,
                email or "",
                notes or "",
                marketing_consent,
                birth_date or "",
            )
            self._customer_service.update_customer(existing.id, customer)
            self._audit("CUSTOMER_UPDATED_FROM_CSV", existing.id, f"row={row.row_number}")
        return existing.id, False, changed

    def _start_batch(self, preview: ImportPreview) -> int:
        self._audit("CSV_IMPORT_STARTED", None, f"file={preview.file_name};hash={preview.file_hash}")
        with sqlite3.connect(self._database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO csv_import_batches (file_name, file_hash, user_id, total_rows, status)
                VALUES (?, ?, ?, ?, 'started')
                ON CONFLICT(file_hash) DO UPDATE SET
                    imported_at = CURRENT_TIMESTAMP,
                    total_rows = excluded.total_rows,
                    status = 'started'
                """,
                (preview.file_name, preview.file_hash, self._current_user.id, preview.total_rows),
            )
            if cursor.lastrowid:
                return int(cursor.lastrowid)
            row = connection.execute(
                "SELECT id FROM csv_import_batches WHERE file_hash = ?",
                (preview.file_hash,),
            ).fetchone()
            return int(row[0])

    def _complete_batch(self, batch_id: int, totals: dict[str, int]) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                UPDATE csv_import_batches
                SET customers_created = ?,
                    customers_updated = ?,
                    purchases_created = ?,
                    rows_skipped = ?,
                    rows_error = ?,
                    status = 'completed'
                WHERE id = ?
                """,
                (
                    totals["customers_created"],
                    totals["customers_updated"],
                    totals["purchases_created"],
                    totals["rows_skipped"],
                    totals["rows_error"],
                    batch_id,
                ),
            )

    def _record_row(self, batch_id: int, result: ImportRowResult) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO csv_import_rows (
                    batch_id, row_number, customer_id, status, message, purchases_created
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (batch_id, result.row_number, result.customer_id, result.status, result.message, result.purchases_created),
            )

    def _duplicate_batch_message(self, file_hash: str) -> str | None:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT imported_at
                FROM csv_import_batches
                WHERE file_hash = ? AND status = 'completed'
                ORDER BY imported_at DESC
                LIMIT 1
                """,
                (file_hash,),
            ).fetchone()
        if not row:
            return None
        imported_at = datetime.fromisoformat(row[0].replace(" ", "T"))
        return f"Este archivo ya fue importado anteriormente el {imported_at.strftime('%d/%m/%Y')} a las {imported_at.strftime('%H:%M')}."

    def _purchase_operation_exists(self, operation_id: str) -> bool:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM purchases WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        return row is not None

    def _customers_by_normalized_phone(self) -> dict[str, CustomerRecord]:
        return {
            normalize_phone(customer.phone or ""): customer
            for customer in self._customer_service.search_customers("")
            if normalize_phone(customer.phone or "")
        }

    def _conflicts(
        self,
        existing: CustomerRecord,
        email: str,
        last_name: str,
        birth_date: str | None,
        notes: str,
    ) -> list[str]:
        conflicts = []
        if existing.email and email and existing.email.strip().lower() != email.strip().lower():
            conflicts.append("Conflicto de correo: no se sobrescribirá automáticamente.")
        if existing.last_name and last_name and existing.last_name.strip().lower() != last_name.strip().lower():
            conflicts.append("Conflicto de apellido: no se sobrescribirá automáticamente.")
        if existing.birth_date and birth_date and existing.birth_date != birth_date:
            conflicts.append("Conflicto de fecha de nacimiento: no se sobrescribirá automáticamente.")
        if existing.notes and notes and existing.notes.strip() != notes.strip():
            conflicts.append("Conflicto de observaciones: no se sobrescribirá automáticamente.")
        return conflicts

    def _audit(self, action: str, entity_id: int | None, value: str) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO audit_logs (user_id, action, entity, entity_id, new_value)
                VALUES (?, ?, 'csv_import', ?, ?)
                """,
                (self._current_user.id, action, entity_id, value),
            )

    @staticmethod
    def _row_name(row: ImportRowPreview) -> str:
        return f"{row.first_name} {row.last_name}".strip()

    @staticmethod
    def _text(value: str | None) -> str:
        return (value or "").strip()

    @staticmethod
    def _detect_dialect(text: str):
        if not text.strip():
            return csv.excel
        try:
            return csv.Sniffer().sniff(text[:4096], delimiters=",;")
        except csv.Error:
            first_line = text.splitlines()[0] if text.splitlines() else ""
            dialect = csv.excel()
            dialect.delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
            return dialect


def normalize_phone(phone: str) -> str:
    return "".join(character for character in phone.strip() if character.isdigit())


def parse_consent(value: str | None) -> bool:
    cleaned = (value or "").strip().lower()
    return cleaned in {"si", "sí", "true", "1"}


def parse_birth_date(value: str) -> str:
    cleaned = value.strip()
    formats = ("%d/%m/%Y", "%Y-%m-%d")
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            break
        except ValueError:
            parsed = None
    if parsed is None:
        raise CsvImportError("Fecha de nacimiento inválida.")
    if parsed > date.today():
        raise CsvImportError("Fecha de nacimiento futura.")
    if parsed < date(1900, 1, 1):
        raise CsvImportError("Fecha de nacimiento anterior a 01/01/1900.")
    return parsed.isoformat()


def parse_money(value: str) -> Decimal:
    cleaned = value.strip().replace("$", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            cleaned = "".join(parts)
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise CsvImportError("Monto inválido.") from exc
