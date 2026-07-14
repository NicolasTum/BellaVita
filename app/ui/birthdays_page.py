from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.birthday_promotions import BirthdayPromotionCustomer, BirthdayPromotionService
from app.utils.dates import MONTH_NAMES, format_birth_date
from app.utils.paths import export_dir


class BirthdaysPage(QWidget):
    def __init__(
        self,
        birthday_service: BirthdayPromotionService,
        on_back,
        on_open_customer,
        on_edit_customer,
        on_show_history,
        on_show_rewards,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._birthday_service = birthday_service
        self._on_back = on_back
        self._on_open_customer = on_open_customer
        self._on_edit_customer = on_edit_customer
        self._on_show_history = on_show_history
        self._on_show_rewards = on_show_rewards
        self._current_customers: list[BirthdayPromotionCustomer] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Cumpleaños")
        title.setObjectName("SectionTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._on_back)
        header.addLayout(title_box, 1)
        header.addWidget(back_button)

        filters = QHBoxLayout()
        self.month_input = QComboBox()
        for month, name in MONTH_NAMES.items():
            self.month_input.addItem(name, month)
        self.month_input.setCurrentIndex(date.today().month - 1)
        self.month_input.currentIndexChanged.connect(self.refresh)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, apellido, teléfono o correo")
        self.search_input.textChanged.connect(self.refresh)
        export_button = QPushButton("Exportar cumpleaños del mes")
        export_button.clicked.connect(self._export)
        filters.addWidget(QLabel("Mes"))
        filters.addWidget(self.month_input)
        filters.addWidget(self.search_input, 1)
        filters.addWidget(export_button)

        cards = QGridLayout()
        cards.setSpacing(10)
        self.total_card = self._metric_label()
        self.phone_card = self._metric_label()
        self.email_card = self._metric_label()
        self.reward_card = self._metric_label()
        cards.addWidget(self.total_card, 0, 0)
        cards.addWidget(self.phone_card, 0, 1)
        cards.addWidget(self.email_card, 0, 2)
        cards.addWidget(self.reward_card, 0, 3)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("DetailInfo")

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Cliente",
                "Día del cumpleaños",
                "Fecha de nacimiento",
                "Teléfono",
                "Correo",
                "Última compra",
                "Premios disponibles",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self._open_selected_customer)

        actions = QHBoxLayout()
        open_button = QPushButton("Abrir ficha")
        open_button.clicked.connect(self._open_selected_customer)
        edit_button = QPushButton("Editar cliente")
        edit_button.clicked.connect(self._edit_selected_customer)
        history_button = QPushButton("Ver historial")
        history_button.clicked.connect(self._history_selected_customer)
        rewards_button = QPushButton("Ver premios disponibles")
        rewards_button.clicked.connect(self._rewards_selected_customer)
        actions.addWidget(open_button)
        actions.addWidget(edit_button)
        actions.addWidget(history_button)
        actions.addWidget(rewards_button)
        actions.addStretch(1)

        layout.addLayout(header)
        layout.addLayout(filters)
        layout.addLayout(cards)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)
        layout.addLayout(actions)

    def refresh(self) -> None:
        month = self.month_input.currentData()
        month_name = MONTH_NAMES[month].lower()
        self._current_customers = self._birthday_service.list_birthdays_for_month(
            month,
            search_text=self.search_input.text() if hasattr(self, "search_input") else "",
        )
        count = len(self._current_customers)
        self.subtitle.setText(f"Cumpleaños de {month_name}")
        if count:
            self.summary_label.setText(f"{count} cliente(s) cumplen años en {month_name}.")
        else:
            self.summary_label.setText(f"No hay clientes con cumpleaños registrados en {month_name}.")

        with_phone = sum(1 for customer in self._current_customers if customer.phone)
        with_email = sum(1 for customer in self._current_customers if customer.email)
        with_rewards = sum(1 for customer in self._current_customers if customer.available_rewards > 0)
        self.total_card.setText(f"Cumpleaños del mes\n{count}")
        self.phone_card.setText(f"Con teléfono\n{with_phone}")
        self.email_card.setText(f"Con correo\n{with_email}")
        self.reward_card.setText(f"Con premio disponible\n{with_rewards}")

        self.table.setRowCount(count)
        for row, customer in enumerate(self._current_customers):
            values = [
                f"{customer.first_name} {customer.last_name}",
                f"{customer.birthday_day:02d} de {customer.birthday_month_name.lower()}",
                format_birth_date(customer.birth_date),
                customer.phone or "",
                customer.email or "",
                customer.last_purchase_at or "",
                str(customer.available_rewards),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, customer.id)
                self.table.setItem(row, column, item)

    def _selected_customer_id(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar cliente", "Seleccioná un cliente de la lista.")
            return None
        return int(self.table.item(selected[0].row(), 0).data(Qt.UserRole))

    def _open_selected_customer(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is not None:
            self._on_open_customer(customer_id)

    def _edit_selected_customer(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is not None:
            self._on_edit_customer(customer_id)

    def _history_selected_customer(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is not None:
            self._on_show_history(customer_id)

    def _rewards_selected_customer(self) -> None:
        customer_id = self._selected_customer_id()
        if customer_id is not None:
            self._on_show_rewards(customer_id)

    def _export(self) -> None:
        month = self.month_input.currentData()
        destination = export_dir() / f"cumpleanos_{month:02d}.csv"
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar cumpleaños",
            str(destination),
            "CSV (*.csv)",
        )
        if not file_name:
            return
        path = self._birthday_service.export_birthdays_for_month(
            month,
            destination=Path(file_name),
            search_text=self.search_input.text(),
        )
        QMessageBox.information(self, "Exportación creada", f"Archivo generado:\n{path}")

    @staticmethod
    def _metric_label() -> QLabel:
        label = QLabel()
        label.setObjectName("DetailInfo")
        label.setAlignment(Qt.AlignCenter)
        return label
