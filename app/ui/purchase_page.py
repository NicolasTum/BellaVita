from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import SETTINGS
from app.repositories.customers import CustomerRecord
from app.services.customers import CustomerService
from app.services.purchases import PurchaseResult, PurchaseService, PurchaseValidationError
from app.utils.money import format_money, to_decimal


class PurchasePage(QWidget):
    def __init__(
        self,
        customer_service: CustomerService,
        purchase_service: PurchaseService,
        on_back,
        on_saved,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._customer_service = customer_service
        self._purchase_service = purchase_service
        self._on_back = on_back
        self._on_saved = on_saved
        self._selected_customer: CustomerRecord | None = None
        self._saving = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        title = QLabel("Registrar compra")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Seleccioná un cliente y registrá una compra simple o detallada.")
        subtitle.setObjectName("Subtitle")

        top_actions = QHBoxLayout()
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._on_back)
        top_actions.addWidget(back_button)
        top_actions.addStretch(1)

        self.customer_search_input = QLineEdit()
        self.customer_search_input.setPlaceholderText("Buscar cliente por nombre, telefono, correo o ID")
        self.customer_search_input.textChanged.connect(self._refresh_customer_table)

        self.customer_table = QTableWidget(0, 5)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Cliente", "Telefono", "Stickers", "Estado"])
        self.customer_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.customer_table.doubleClicked.connect(self._select_current_row)

        select_button = QPushButton("Seleccionar cliente")
        select_button.clicked.connect(self._select_current_row)

        self.customer_info = QLabel("Cliente seleccionado: ninguno")
        self.customer_info.setObjectName("DetailInfo")
        self.customer_info.setWordWrap(True)

        mode_row = QHBoxLayout()
        self.mode_input = QComboBox()
        self.mode_input.addItems(["Simple", "Detallada"])
        self.mode_input.currentTextChanged.connect(self._sync_mode)
        mode_row.addWidget(QLabel("Modalidad"))
        mode_row.addWidget(self.mode_input)
        mode_row.addStretch(1)

        self.summary_input = QLineEdit()
        self.summary_input.setPlaceholderText("Descripción general")
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Importe total")
        self.amount_input.textChanged.connect(self._recalculate_detail_total)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Observaciones")
        self.notes_input.setFixedHeight(70)

        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio unitario", "Subtotal"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.itemChanged.connect(self._recalculate_detail_total)
        add_item_button = QPushButton("Agregar producto")
        add_item_button.clicked.connect(self._add_item_row)
        remove_item_button = QPushButton("Quitar producto")
        remove_item_button.clicked.connect(self._remove_selected_item)
        item_actions = QHBoxLayout()
        item_actions.addWidget(add_item_button)
        item_actions.addWidget(remove_item_button)
        item_actions.addStretch(1)

        self.total_label = QLabel("Total: $ 0.00")
        self.total_label.setObjectName("SectionTitle")

        self.save_button = QPushButton("Guardar compra")
        self.save_button.clicked.connect(self._save_purchase)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(top_actions)
        layout.addWidget(self.customer_search_input)
        layout.addWidget(self.customer_table)
        layout.addWidget(select_button)
        layout.addWidget(self.customer_info)
        layout.addLayout(mode_row)
        layout.addWidget(self.summary_input)
        layout.addWidget(self.amount_input)
        layout.addWidget(self.items_table)
        layout.addLayout(item_actions)
        layout.addWidget(self.notes_input)
        layout.addWidget(self.total_label)
        layout.addWidget(self.save_button)

        self._add_item_row()
        self._sync_mode()

    def refresh(self) -> None:
        self._refresh_customer_table()
        self._refresh_selected_customer()

    def preselect_customer(self, customer_id: int) -> None:
        customer = self._customer_service.get_customer(customer_id)
        if customer:
            self._selected_customer = customer
            self._update_customer_info()
        self.refresh()

    def _refresh_customer_table(self) -> None:
        customers = self._customer_service.search_customers(self.customer_search_input.text())
        self.customer_table.setRowCount(len(customers))
        for row_index, customer in enumerate(customers):
            values = [
                str(customer.id),
                customer.full_name,
                customer.phone or "",
                f"{customer.current_stickers}/{SETTINGS.stickers_per_cycle}",
                "Activo" if customer.is_active else "Inactivo",
            ]
            for column_index, value in enumerate(values):
                self.customer_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _select_current_row(self) -> None:
        selected = self.customer_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar cliente", "Seleccioná un cliente de la lista.")
            return
        customer_id = int(self.customer_table.item(selected[0].row(), 0).text())
        self._selected_customer = self._customer_service.get_customer(customer_id)
        self._update_customer_info()

    def _refresh_selected_customer(self) -> None:
        if self._selected_customer:
            self._selected_customer = self._customer_service.get_customer(self._selected_customer.id)
            self._update_customer_info()

    def _update_customer_info(self) -> None:
        customer = self._selected_customer
        if not customer:
            self.customer_info.setText("Cliente seleccionado: ninguno")
            return
        self.customer_info.setText(
            "\n".join(
                [
                    f"Cliente: {customer.full_name}",
                    f"Telefono: {customer.phone or '-'}",
                    f"Correo: {customer.email or '-'}",
                    f"Estado: {'Activo' if customer.is_active else 'Inactivo'}",
                    f"Stickers actuales: {customer.current_stickers}/{SETTINGS.stickers_per_cycle}",
                    f"Premios disponibles: {customer.available_rewards}",
                ]
            )
        )

    def _sync_mode(self) -> None:
        detailed = self.mode_input.currentText() == "Detallada"
        self.amount_input.setVisible(not detailed)
        self.items_table.setVisible(detailed)
        self._recalculate_detail_total()

    def _add_item_row(self) -> None:
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        defaults = ["", "1", "0", "0.00"]
        for column, value in enumerate(defaults):
            item = QTableWidgetItem(value)
            if column == 3:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, column, item)

    def _remove_selected_item(self) -> None:
        row = self.items_table.currentRow()
        if row >= 0:
            self.items_table.removeRow(row)
        if self.items_table.rowCount() == 0:
            self._add_item_row()
        self._recalculate_detail_total()

    def _recalculate_detail_total(self) -> None:
        if not hasattr(self, "items_table"):
            return
        total = Decimal("0.00")
        self.items_table.blockSignals(True)
        for row in range(self.items_table.rowCount()):
            try:
                quantity = to_decimal(self._table_text(row, 1))
                unit_price = to_decimal(self._table_text(row, 2))
                subtotal = quantity * unit_price
            except ValueError:
                subtotal = Decimal("0.00")
            total += subtotal
            if self.items_table.item(row, 3) is None:
                self.items_table.setItem(row, 3, QTableWidgetItem("0.00"))
            self.items_table.item(row, 3).setText(str(subtotal.quantize(Decimal("0.01"))))
        self.items_table.blockSignals(False)
        if self.mode_input.currentText() == "Detallada":
            self.total_label.setText(f"Total: {format_money(total)}")
        else:
            try:
                total = to_decimal(self.amount_input.text())
            except ValueError:
                total = Decimal("0.00")
            self.total_label.setText(f"Total: {format_money(total)}")

    def _save_purchase(self) -> None:
        if self._saving:
            return
        customer = self._selected_customer
        if not customer:
            QMessageBox.warning(self, "Cliente obligatorio", "Seleccioná un cliente antes de guardar.")
            return
        if not customer.is_active:
            QMessageBox.warning(self, "Cliente inactivo", "No se pueden registrar compras para clientes inactivos.")
            return

        try:
            if self.mode_input.currentText() == "Detallada":
                purchase = self._purchase_service.build_detailed_purchase(
                    customer_id=customer.id,
                    items=[
                        (
                            self._table_text(row, 0),
                            self._table_text(row, 1),
                            self._table_text(row, 2),
                        )
                        for row in range(self.items_table.rowCount())
                    ],
                    notes=self.notes_input.toPlainText(),
                )
            else:
                purchase = self._purchase_service.build_simple_purchase(
                    customer_id=customer.id,
                    summary=self.summary_input.text(),
                    total_amount=self.amount_input.text(),
                    notes=self.notes_input.toPlainText(),
                )
        except (PurchaseValidationError, ValueError) as exc:
            QMessageBox.warning(self, "Revisar compra", str(exc))
            return

        answer = QMessageBox.question(
            self,
            "Confirmar compra",
            f"¿Confirma registrar esta compra por {format_money(purchase.total_amount)} "
            f"para {customer.full_name}?",
        )
        if answer != QMessageBox.Yes:
            return

        self._saving = True
        self.save_button.setEnabled(False)
        try:
            result = self._purchase_service.register_purchase(purchase)
        except PurchaseValidationError as exc:
            QMessageBox.warning(self, "No se pudo guardar", str(exc))
            return
        finally:
            self._saving = False
            self.save_button.setEnabled(True)

        message = (
            f"Compra guardada. Sticker {result.sticker_number}/{SETTINGS.stickers_per_cycle}.\n"
            f"Faltan {result.missing_count} compra(s)."
        )
        if result.cycle_completed and result.reward_value is not None:
            message += f"\nCiclo completado. Premio disponible: {format_money(result.reward_value)}."
        QMessageBox.information(self, "Compra registrada", message)
        self._clear_form()
        self._on_saved(result)

    def _clear_form(self) -> None:
        self.summary_input.clear()
        self.amount_input.clear()
        self.notes_input.clear()
        self.items_table.setRowCount(0)
        self._add_item_row()
        self._refresh_selected_customer()
        self._refresh_customer_table()
        self._recalculate_detail_total()

    def _table_text(self, row: int, column: int) -> str:
        item = self.items_table.item(row, column)
        return item.text().strip() if item else ""
