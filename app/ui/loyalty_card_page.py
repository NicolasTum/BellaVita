from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import SETTINGS
from app.repositories.customers import CustomerRecord
from app.repositories.loyalty import LoyaltyRepository
from app.services.customers import CustomerService
from app.utils.money import format_money


class LoyaltyCardPage(QWidget):
    def __init__(
        self,
        customer_service: CustomerService,
        loyalty_repository: LoyaltyRepository,
        on_back,
        on_register_purchase,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._customer_service = customer_service
        self._loyalty_repository = loyalty_repository
        self._on_back = on_back
        self._on_register_purchase = on_register_purchase
        self._customer_id: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        self.title = QLabel("Carton de fidelizacion")
        self.title.setObjectName("SectionTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Subtitle")

        self.summary = QLabel()
        self.summary.setObjectName("DetailInfo")
        self.summary.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, SETTINGS.stickers_per_cycle)

        self.sticker_grid = QGridLayout()
        self.sticker_labels: list[QLabel] = []
        self._ensure_sticker_labels(SETTINGS.stickers_per_cycle)

        self.cycles_table = QTableWidget(0, 5)
        self.cycles_table.setHorizontalHeaderLabels(["Ciclo", "Estado", "Compras", "Total", "Promedio"])

        actions = QHBoxLayout()
        back_button = QPushButton("Volver a ficha")
        back_button.clicked.connect(self._on_back)
        purchase_button = QPushButton("Registrar nueva compra")
        purchase_button.clicked.connect(self._register_purchase)
        history_button = QPushButton("Ver historial de ciclos")
        history_button.clicked.connect(lambda: self.cycles_table.setFocus())
        actions.addWidget(back_button)
        actions.addWidget(purchase_button)
        actions.addWidget(history_button)
        actions.addStretch(1)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.summary)
        layout.addWidget(self.progress)
        layout.addLayout(self.sticker_grid)
        layout.addWidget(QLabel("Historial de ciclos"))
        layout.addWidget(self.cycles_table)
        layout.addLayout(actions)

    def show_customer(self, customer_id: int) -> None:
        self._customer_id = customer_id
        self.refresh()

    def refresh(self) -> None:
        if self._customer_id is None:
            return
        customer = self._customer_service.get_customer(self._customer_id)
        if not customer:
            return
        loyalty = self._loyalty_repository.summary_for_customer(customer.id)
        cycle = loyalty.current_cycle or loyalty.latest_cycle

        self.title.setText(f"Carton de {customer.full_name}")
        if cycle:
            self.subtitle.setText(
                f"Ciclo {cycle.cycle_number} - "
                f"{'EN PROGRESO' if cycle.status == 'in_progress' else 'COMPLETADO'}"
            )
            target = cycle.target_purchase_count
            count = cycle.valid_purchase_count
            total = cycle.total_amount
            average = cycle.average_amount
        else:
            self.subtitle.setText("Sin ciclo iniciado")
            target = SETTINGS.stickers_per_cycle
            count = 0
            total = average = None

        self._ensure_sticker_labels(target)
        missing = max(0, target - count)
        self.progress.setRange(0, target)
        self.progress.setValue(count)
        self.summary.setText(
            "\n".join(
                [
                    f"Cliente: {customer.full_name}",
                    f"Compras completadas: {count}/{target}",
                    f"Compras faltantes: {missing}",
                    f"Total acumulado: {format_money(total) if total is not None else '$ 0.00'}",
                    f"Promedio parcial/final: {format_money(average) if average is not None else '$ 0.00'}",
                    f"Premios disponibles: {loyalty.available_rewards}",
                ]
            )
        )

        for sticker in loyalty.stickers:
            label = self.sticker_labels[sticker.sticker_number - 1]
            if sticker.purchased_at:
                label.setText(
                    f"Sticker {sticker.sticker_number}\n"
                    f"COMPLETO\n{sticker.purchased_at}\n"
                    f"{format_money(sticker.total_amount)}\n{sticker.summary}"
                )
                label.setProperty("complete", True)
            else:
                label.setText(f"Sticker {sticker.sticker_number}\nPendiente")
                label.setProperty("complete", False)
            label.style().unpolish(label)
            label.style().polish(label)

        cycles = self._loyalty_repository.cycles_for_customer(customer.id)
        self.cycles_table.setRowCount(len(cycles))
        for row_index, cycle_row in enumerate(cycles):
            values = [
                str(cycle_row.cycle_number),
                "EN PROGRESO" if cycle_row.status == "in_progress" else "COMPLETADO",
                f"{cycle_row.valid_purchase_count}/{cycle_row.target_purchase_count}",
                format_money(cycle_row.total_amount),
                format_money(cycle_row.average_amount),
            ]
            for column_index, value in enumerate(values):
                self.cycles_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _register_purchase(self) -> None:
        if self._customer_id is not None:
            self._on_register_purchase(self._customer_id)

    def _ensure_sticker_labels(self, target: int) -> None:
        while len(self.sticker_labels) < target:
            index = len(self.sticker_labels)
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setObjectName("Sticker")
            label.setMinimumHeight(96)
            label.setWordWrap(True)
            self.sticker_labels.append(label)
            self.sticker_grid.addWidget(label, index // 4, index % 4)
        for index, label in enumerate(self.sticker_labels):
            label.setVisible(index < target)
