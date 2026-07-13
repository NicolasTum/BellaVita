from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
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
from app.ui.customer_dialog import CustomerDialog
from app.utils.money import format_money, money_from_db, to_decimal


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
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Registrar compra")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Seleccioná un cliente y registrá una compra simple o detallada.")
        subtitle.setObjectName("Subtitle")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._on_back)
        header.addLayout(header_text, 1)
        header.addStretch(1)
        header.addWidget(back_button, 0, Qt.AlignTop)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self._build_client_panel())
        self.splitter.addWidget(self._build_purchase_panel())
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 35)
        self.splitter.setStretchFactor(1, 65)

        layout.addLayout(header)
        layout.addWidget(self.splitter, 1)

        self._sync_mode()
        self._update_customer_info()
        self.splitter.setSizes([380, 720])

    def _build_client_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setMinimumWidth(320)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Clientes")
        title.setObjectName("CardTitle")

        self.customer_search_input = QLineEdit()
        self.customer_search_input.setPlaceholderText("Nombre, apellido, telefono, correo o ID")
        self.customer_search_input.textChanged.connect(self._refresh_customer_table)

        self.customer_table = QTableWidget(0, 5)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Cliente", "Telefono", "Stickers", "Estado"])
        self.customer_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customer_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.customer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.verticalHeader().setVisible(False)
        self.customer_table.horizontalHeader().setVisible(True)
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.customer_table.doubleClicked.connect(self._select_current_row)

        self.customer_count_label = QLabel("0 clientes mostrados")
        self.customer_count_label.setObjectName("Hint")

        self.select_customer_button = QPushButton("Seleccionar cliente")
        self.select_customer_button.setObjectName("PrimaryButton")
        self.select_customer_button.clicked.connect(self._select_current_row)

        secondary_actions = QHBoxLayout()
        new_customer_button = QPushButton("Nuevo cliente")
        new_customer_button.clicked.connect(self._open_new_customer)
        refresh_button = QPushButton("Refrescar lista")
        refresh_button.clicked.connect(self._refresh_customer_table)
        secondary_actions.addWidget(new_customer_button)
        secondary_actions.addWidget(refresh_button)

        layout.addWidget(title)
        layout.addWidget(self.customer_search_input)
        layout.addWidget(self.customer_table, 1)
        layout.addWidget(self.customer_count_label)
        layout.addWidget(self.select_customer_button)
        layout.addLayout(secondary_actions)
        return panel

    def _build_purchase_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("PurchaseScroll")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 0, 4, 0)
        content_layout.setSpacing(14)

        self.customer_card = QFrame()
        self.customer_card.setObjectName("InfoCard")
        card_layout = QVBoxLayout(self.customer_card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        card_title = QLabel("Cliente seleccionado")
        card_title.setObjectName("CardTitle")
        self.selected_customer_name = QLabel("Seleccione un cliente de la lista para registrar una compra.")
        self.selected_customer_name.setObjectName("SelectedCustomerName")
        self.selected_customer_name.setWordWrap(True)
        self.selected_customer_details = QLabel("")
        self.selected_customer_details.setObjectName("DetailText")
        self.selected_customer_details.setWordWrap(True)
        self.cycle_progress = QProgressBar()
        self.cycle_progress.setRange(0, SETTINGS.stickers_per_cycle)
        self.cycle_progress.setTextVisible(True)
        card_layout.addWidget(card_title)
        card_layout.addWidget(self.selected_customer_name)
        card_layout.addWidget(self.selected_customer_details)
        card_layout.addWidget(self.cycle_progress)

        form_card = QFrame()
        form_card.setObjectName("InfoCard")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_layout.setSpacing(12)

        form_title = QLabel("Datos de la compra")
        form_title.setObjectName("CardTitle")

        mode_row = QHBoxLayout()
        self.mode_input = QComboBox()
        self.mode_input.addItems(["Simple", "Detallada"])
        self.mode_input.currentTextChanged.connect(self._sync_mode)
        mode_row.addWidget(QLabel("Modalidad"))
        mode_row.addWidget(self.mode_input)
        mode_row.addStretch(1)

        self.simple_fields = QWidget()
        simple_layout = QGridLayout(self.simple_fields)
        simple_layout.setContentsMargins(0, 0, 0, 0)
        simple_layout.setHorizontalSpacing(12)
        simple_layout.setVerticalSpacing(8)
        self.summary_input = QLineEdit()
        self.summary_input.setPlaceholderText("Descripción general")
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Importe total")
        self.amount_input.textChanged.connect(self._recalculate_detail_total)
        simple_layout.addWidget(QLabel("Descripción"), 0, 0)
        simple_layout.addWidget(QLabel("Importe total"), 0, 1)
        simple_layout.addWidget(self.summary_input, 1, 0)
        simple_layout.addWidget(self.amount_input, 1, 1)
        simple_layout.setColumnStretch(0, 2)
        simple_layout.setColumnStretch(1, 1)

        self.detail_fields = QWidget()
        detail_layout = QVBoxLayout(self.detail_fields)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(8)
        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels(["Descripción", "Cantidad", "Precio unitario", "Subtotal"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.itemChanged.connect(self._recalculate_detail_total)
        self.items_table.setMinimumHeight(180)
        self.add_item_button = QPushButton("Agregar producto")
        self.add_item_button.clicked.connect(self._add_item_row)
        self.remove_item_button = QPushButton("Quitar producto")
        self.remove_item_button.clicked.connect(self._remove_selected_item)
        item_actions = QHBoxLayout()
        item_actions.addWidget(self.add_item_button)
        item_actions.addWidget(self.remove_item_button)
        item_actions.addStretch(1)
        detail_layout.addWidget(self.items_table)
        detail_layout.addLayout(item_actions)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Observaciones")
        self.notes_input.setFixedHeight(76)

        total_row = QHBoxLayout()
        self.total_label = QLabel("Total: $ 0.00")
        self.total_label.setObjectName("TotalLabel")
        total_row.addStretch(1)
        total_row.addWidget(self.total_label)

        self.save_button = QPushButton("Guardar compra")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self._save_purchase)

        form_layout.addWidget(form_title)
        form_layout.addLayout(mode_row)
        form_layout.addWidget(self.simple_fields)
        form_layout.addWidget(self.detail_fields)
        form_layout.addWidget(QLabel("Observaciones"))
        form_layout.addWidget(self.notes_input)
        form_layout.addLayout(total_row)
        form_layout.addWidget(self.save_button)

        content_layout.addWidget(self.customer_card)
        content_layout.addWidget(form_card)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def refresh(self) -> None:
        self._refresh_customer_table()
        self._refresh_selected_customer()
        self._update_save_enabled()

    def preselect_customer(self, customer_id: int) -> None:
        customer = self._customer_service.get_customer(customer_id)
        if customer:
            self._selected_customer = customer
            self._update_customer_info()
        self.refresh()

    def reset_for_next_purchase(self) -> None:
        self._selected_customer = None
        self.customer_table.clearSelection()
        self._clear_form(clear_customer=True)
        self.customer_search_input.clear()
        self._refresh_customer_table()
        self.customer_search_input.setFocus()

    def _refresh_customer_table(self) -> None:
        customers = self._customer_service.search_customers(self.customer_search_input.text())
        self.customer_table.setRowCount(len(customers))
        for row_index, customer in enumerate(customers):
            target = customer.current_cycle_target
            values = [
                str(customer.id),
                customer.full_name,
                customer.phone or "",
                f"{customer.current_stickers}/{target}",
                "Activo" if customer.is_active else "Inactivo",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(Qt.UserRole, customer.id)
                self.customer_table.setItem(row_index, column_index, item)
        self.customer_count_label.setText(f"{len(customers)} cliente(s) mostrados")

    def _select_current_row(self) -> None:
        selected = self.customer_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar cliente", "Seleccioná un cliente de la lista.")
            return
        customer_id = int(self.customer_table.item(selected[0].row(), 0).text())
        self._selected_customer = self._customer_service.get_customer(customer_id)
        self._update_customer_info()

    def _open_new_customer(self) -> None:
        dialog = CustomerDialog(self._customer_service, self)
        if dialog.exec() and dialog.saved_customer_id:
            self.customer_search_input.clear()
            self._refresh_customer_table()
            self.preselect_customer(dialog.saved_customer_id)

    def _refresh_selected_customer(self) -> None:
        if self._selected_customer:
            self._selected_customer = self._customer_service.get_customer(self._selected_customer.id)
            self._update_customer_info()

    def _update_customer_info(self) -> None:
        customer = self._selected_customer
        if not customer:
            self.selected_customer_name.setText("Seleccione un cliente de la lista para registrar una compra.")
            self.selected_customer_details.setText("")
            self.cycle_progress.setValue(0)
            self.cycle_progress.setFormat("0/%m stickers")
            self._update_save_enabled()
            return

        target = customer.current_cycle_target
        missing = max(0, target - customer.current_stickers)
        cycle_state = "En progreso" if customer.current_stickers else "Sin compras en ciclo actual"
        if customer.current_stickers == target:
            cycle_state = "Ciclo completo"

        self.selected_customer_name.setText(customer.full_name)
        self.selected_customer_details.setText(
            "\n".join(
                [
                    f"Teléfono: {customer.phone or '-'}",
                    f"Correo: {customer.email or '-'}",
                    f"Estado: {'Activo' if customer.is_active else 'Inactivo'}",
                    f"Stickers: {customer.current_stickers}/{target}",
                    f"Ciclo actual: {cycle_state}",
                    f"Faltan {missing} compra(s)",
                    f"Promedio parcial: {format_money(money_from_db(customer.current_cycle_average))}",
                ]
            )
        )
        self.cycle_progress.setRange(0, target)
        self.cycle_progress.setValue(customer.current_stickers)
        self.cycle_progress.setFormat(f"{customer.current_stickers}/{target} stickers")
        self._update_save_enabled()

    def _sync_mode(self) -> None:
        detailed = self.mode_input.currentText() == "Detallada"
        self.simple_fields.setVisible(not detailed)
        self.detail_fields.setVisible(detailed)
        if detailed and self.items_table.rowCount() == 0:
            self._add_item_row()
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
            self._update_save_enabled()

        message = (
            "Compra registrada correctamente.\n\n"
            f"Cliente: {customer.full_name}\n"
            f"Importe: {format_money(result.total_amount)}\n"
            f"Sticker: {result.sticker_number} de {result.target_purchase_count}\n"
            f"Faltan {result.missing_count} compra(s)."
        )
        if result.cycle_completed and result.reward_value is not None:
            message += f"\nPremio generado: {format_money(result.reward_value)}."
        message += "\n\nPuede registrar la siguiente compra."
        QMessageBox.information(self, "Compra registrada", message)
        self._on_saved(result)
        self.reset_for_next_purchase()

    def _clear_form(self, clear_customer: bool = False) -> None:
        if clear_customer:
            self._selected_customer = None
        self.summary_input.clear()
        self.amount_input.clear()
        self.notes_input.clear()
        self.items_table.setRowCount(0)
        self._add_item_row()
        if not clear_customer:
            self._refresh_selected_customer()
        else:
            self._update_customer_info()
        self._refresh_customer_table()
        self._recalculate_detail_total()

    def _update_save_enabled(self) -> None:
        customer = self._selected_customer
        self.save_button.setEnabled(bool(customer and customer.is_active and not self._saving))

    def _table_text(self, row: int, column: int) -> str:
        item = self.items_table.item(row, column)
        return item.text().strip() if item else ""
