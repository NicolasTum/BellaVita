from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.csv_import import CsvImportError, CsvImportService, ImportPreview, ImportResult
from app.utils.money import format_money
from app.utils.paths import export_dir


class CsvImportPage(QWidget):
    def __init__(self, import_service: CsvImportService, parent=None) -> None:
        super().__init__(parent)
        self._import_service = import_service
        self._selected_file: Path | None = None
        self._preview: ImportPreview | None = None
        self._last_result: ImportResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        instructions = QLabel(
            "Cada fila representa un cliente. Nombre y teléfono son obligatorios. "
            "Puede incluir hasta seis compras históricas."
        )
        instructions.setObjectName("Hint")
        instructions.setWordWrap(True)

        actions = QHBoxLayout()
        template_button = QPushButton("Descargar plantilla CSV")
        template_button.clicked.connect(self._download_template)
        select_button = QPushButton("Seleccionar archivo")
        select_button.clicked.connect(self._select_file)
        analyze_button = QPushButton("Analizar archivo")
        analyze_button.clicked.connect(self.analyze_selected_file)
        import_button = QPushButton("Importar registros")
        import_button.clicked.connect(self._import_records)
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self._clear)
        actions.addWidget(template_button)
        actions.addWidget(select_button)
        actions.addWidget(analyze_button)
        actions.addWidget(import_button)
        actions.addWidget(cancel_button)
        actions.addStretch(1)

        options = QHBoxLayout()
        self.existing_behavior_input = QComboBox()
        self.existing_behavior_input.addItem(
            "Actualizar campos vacíos y agregar compras",
            "update_empty_and_add_purchases",
        )
        self.existing_behavior_input.addItem("Solo agregar compras", "add_purchases_only")
        self.existing_behavior_input.addItem("Omitir cliente existente", "skip_existing")
        self.mode_input = QComboBox()
        self.mode_input.addItem("Importar solamente filas válidas", "partial")
        self.mode_input.addItem("Cancelar toda la importación si hay errores", "all_or_nothing")
        self.filter_input = QComboBox()
        for label, value in (
            ("Todos", "all"),
            ("Válidos", "valid"),
            ("Advertencias", "warning"),
            ("Errores", "error"),
            ("Existentes", "existing"),
        ):
            self.filter_input.addItem(label, value)
        self.filter_input.currentIndexChanged.connect(self._refresh_table)
        options.addWidget(QLabel("Existentes"))
        options.addWidget(self.existing_behavior_input)
        options.addWidget(QLabel("Modo"))
        options.addWidget(self.mode_input)
        options.addWidget(QLabel("Filtro"))
        options.addWidget(self.filter_input)
        options.addStretch(1)

        self.file_label = QLabel("Archivo: no seleccionado")
        self.file_label.setObjectName("Hint")
        self.summary_label = QLabel("Vista previa pendiente.")
        self.summary_label.setObjectName("DetailInfo")
        self.summary_label.setWordWrap(True)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Fila",
                "Nombre",
                "Apellido",
                "Teléfono",
                "Correo",
                "Fecha de nacimiento",
                "Compras encontradas",
                "Total importado",
                "Estado / Observaciones",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        layout.addWidget(instructions)
        layout.addLayout(actions)
        layout.addLayout(options)
        layout.addWidget(self.file_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)

    def analyze_selected_file(self) -> None:
        if not self._selected_file:
            QMessageBox.information(self, "Seleccionar archivo", "Seleccioná un archivo CSV primero.")
            return
        try:
            self._preview = self._import_service.analyze_file(self._selected_file)
        except CsvImportError as exc:
            QMessageBox.warning(self, "No se pudo analizar", str(exc))
            return
        self._refresh_table()

    def _download_template(self) -> None:
        try:
            csv_path, instructions_path = self._import_service.write_template()
        except CsvImportError as exc:
            QMessageBox.warning(self, "No se pudo crear plantilla", str(exc))
            return
        QMessageBox.information(
            self,
            "Plantilla creada",
            f"Archivos generados:\n{csv_path}\n{instructions_path}",
        )

    def _select_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar CSV",
            str(export_dir()),
            "CSV (*.csv)",
        )
        if not file_name:
            return
        self._selected_file = Path(file_name)
        self.file_label.setText(f"Archivo: {self._selected_file}")
        self._preview = None
        self.table.setRowCount(0)
        self.summary_label.setText("Archivo seleccionado. Presioná Analizar archivo.")

    def _import_records(self) -> None:
        if not self._preview:
            QMessageBox.information(self, "Analizar primero", "Analizá el archivo antes de importar.")
            return
        if self._preview.error_count:
            message = f"Hay {self._preview.error_count} fila(s) con error. Se importarán solo las válidas."
            if self.mode_input.currentData() == "all_or_nothing":
                message = "Hay errores y el modo seleccionado cancelará toda la importación."
            if QMessageBox.question(self, "Confirmar importación", message) != QMessageBox.Yes:
                return
        result = self._import_service.import_preview(
            self._preview,
            existing_behavior=self.existing_behavior_input.currentData(),
            mode=self.mode_input.currentData(),
        )
        self._last_result = result
        report_path = self._import_service.write_result_report(
            result,
            export_dir() / "Reporte_Importacion_Clientes.csv",
        )
        self.summary_label.setText(
            f"Filas leídas: {result.total_rows} | Clientes nuevos: {result.customers_created} | "
            f"Clientes actualizados: {result.customers_updated} | Compras importadas: {result.purchases_created} | "
            f"Errores: {result.rows_error}\nReporte: {report_path}"
        )
        QMessageBox.information(self, "Importación finalizada", self.summary_label.text())

    def _clear(self) -> None:
        self._selected_file = None
        self._preview = None
        self._last_result = None
        self.file_label.setText("Archivo: no seleccionado")
        self.summary_label.setText("Vista previa pendiente.")
        self.table.setRowCount(0)

    def _refresh_table(self) -> None:
        if not self._preview:
            return
        rows = list(self._preview.rows)
        selected_filter = self.filter_input.currentData()
        if selected_filter == "valid":
            rows = [row for row in rows if row.status == "Listo para importar"]
        elif selected_filter == "warning":
            rows = [row for row in rows if row.status == "Advertencia"]
        elif selected_filter == "error":
            rows = [row for row in rows if row.status == "Error"]
        elif selected_filter == "existing":
            rows = [row for row in rows if row.existing_customer_id is not None]

        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row.row_number),
                row.first_name,
                row.last_name,
                row.phone,
                row.email,
                row.birth_date or "",
                str(len(row.purchases)),
                format_money(row.total_amount),
                f"{row.status}: {'; '.join(row.messages)}".strip(),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        duplicate = f"\n{self._preview.duplicate_batch_message}" if self._preview.duplicate_batch_message else ""
        self.summary_label.setText(
            f"Filas leídas: {self._preview.total_rows} | Errores: {self._preview.error_count}{duplicate}"
        )
