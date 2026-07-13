from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.repositories.history import CustomerHistoryRepository
from app.services.customers import CustomerService
from app.services.rewards import RewardService
from app.ui.reward_dialogs import RewardDetailDialog, RewardRedeemDialog
from app.utils.money import format_money


class CustomerHistoryPage(QWidget):
    def __init__(
        self,
        customer_service: CustomerService,
        history_repository: CustomerHistoryRepository,
        reward_service: RewardService,
        on_back,
        on_register_purchase,
        on_changed,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._customer_service = customer_service
        self._history_repository = history_repository
        self._reward_service = reward_service
        self._on_back = on_back
        self._on_register_purchase = on_register_purchase
        self._on_changed = on_changed
        self._customer_id: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        self.title = QLabel("Historial del cliente")
        self.title.setObjectName("SectionTitle")
        self.tabs = QTabWidget()
        self.purchases_table = QTableWidget(0, 6)
        self.purchases_table.setHorizontalHeaderLabels(["Fecha", "Ciclo", "Sticker", "Descripción", "Total", "Estado"])
        self.cycles_table = QTableWidget(0, 7)
        self.cycles_table.setHorizontalHeaderLabels(["Ciclo", "Inicio", "Fin", "Compras", "Total", "Promedio", "Estado"])
        self.rewards_table = QTableWidget(0, 6)
        self.rewards_table.setHorizontalHeaderLabels(["ID", "Ciclo", "Generado", "Valor", "Estado", "Uso/Prenda"])
        self.tabs.addTab(self.purchases_table, "Compras")
        self.tabs.addTab(self.cycles_table, "Ciclos")
        self.tabs.addTab(self.rewards_table, "Premios")

        actions = QHBoxLayout()
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._on_back)
        purchase_button = QPushButton("Registrar nueva compra")
        purchase_button.clicked.connect(self._register_purchase)
        view_purchase_button = QPushButton("Ver compra")
        view_purchase_button.clicked.connect(self._view_selected_purchase)
        view_cycle_button = QPushButton("Ver ciclo")
        view_cycle_button.clicked.connect(self._view_selected_cycle)
        reward_button = QPushButton("Canjear premio disponible")
        reward_button.clicked.connect(self._redeem_selected_available_reward)
        view_reward_button = QPushButton("Ver premio")
        view_reward_button.clicked.connect(self._view_selected_reward)
        actions.addWidget(back_button)
        actions.addWidget(purchase_button)
        actions.addWidget(view_purchase_button)
        actions.addWidget(view_cycle_button)
        actions.addWidget(view_reward_button)
        actions.addWidget(reward_button)
        actions.addStretch(1)

        layout.addWidget(self.title)
        layout.addWidget(self.tabs, 1)
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
        self.title.setText(f"Historial de {customer.full_name}")

        purchases = self._history_repository.purchases(customer.id)
        self.purchases_table.setRowCount(len(purchases))
        for row, purchase in enumerate(purchases):
            values = [
                purchase.purchased_at,
                str(purchase.cycle_number),
                str(purchase.sticker_number),
                purchase.summary,
                format_money(purchase.total_amount),
                purchase.status,
            ]
            self._fill_row(self.purchases_table, row, values)

        cycles = self._history_repository.cycles(customer.id)
        self.cycles_table.setRowCount(len(cycles))
        for row, cycle in enumerate(cycles):
            values = [
                str(cycle.cycle_number),
                cycle.started_at,
                cycle.completed_at or "",
                str(cycle.valid_purchase_count),
                format_money(cycle.total_amount),
                format_money(cycle.average_amount),
                cycle.status,
            ]
            self._fill_row(self.cycles_table, row, values)

        rewards = self._history_repository.rewards(customer.id)
        self.rewards_table.setRowCount(len(rewards))
        for row, reward in enumerate(rewards):
            values = [
                str(reward.id),
                str(reward.cycle_number),
                reward.earned_at,
                format_money(reward.max_value),
                reward.status,
                reward.used_at or reward.delivered_item_description or "",
            ]
            self._fill_row(self.rewards_table, row, values)

    def _register_purchase(self) -> None:
        if self._customer_id is not None:
            self._on_register_purchase(self._customer_id)

    def _selected_reward_id(self) -> int | None:
        selected = self.rewards_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar premio", "Seleccioná un premio en la pestaña Premios.")
            return None
        return int(self.rewards_table.item(selected[0].row(), 0).text())

    def _view_selected_purchase(self) -> None:
        selected = self.purchases_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar compra", "Seleccioná una compra en la pestaña Compras.")
            return
        row = selected[0].row()
        QMessageBox.information(
            self,
            "Detalle de compra",
            "\n".join(
                [
                    f"Fecha: {self.purchases_table.item(row, 0).text()}",
                    f"Ciclo: {self.purchases_table.item(row, 1).text()}",
                    f"Sticker: {self.purchases_table.item(row, 2).text()}",
                    f"Descripción: {self.purchases_table.item(row, 3).text()}",
                    f"Total: {self.purchases_table.item(row, 4).text()}",
                    f"Estado: {self.purchases_table.item(row, 5).text()}",
                ]
            ),
        )

    def _view_selected_cycle(self) -> None:
        selected = self.cycles_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar ciclo", "Seleccioná un ciclo en la pestaña Ciclos.")
            return
        row = selected[0].row()
        QMessageBox.information(
            self,
            "Detalle de ciclo",
            "\n".join(
                [
                    f"Ciclo: {self.cycles_table.item(row, 0).text()}",
                    f"Inicio: {self.cycles_table.item(row, 1).text()}",
                    f"Fin: {self.cycles_table.item(row, 2).text() or '-'}",
                    f"Compras: {self.cycles_table.item(row, 3).text()}",
                    f"Total: {self.cycles_table.item(row, 4).text()}",
                    f"Promedio: {self.cycles_table.item(row, 5).text()}",
                    f"Estado: {self.cycles_table.item(row, 6).text()}",
                ]
            ),
        )

    def _view_selected_reward(self) -> None:
        reward_id = self._selected_reward_id()
        if reward_id is None:
            return
        reward = self._reward_service.get_reward(reward_id)
        if reward:
            dialog = RewardDetailDialog(reward, self._reward_service, self)
            if dialog.exec() and dialog.redeemed:
                self.refresh()
                self._on_changed(reward.customer_id)

    def _redeem_selected_available_reward(self) -> None:
        reward_id = self._selected_reward_id()
        if reward_id is None:
            return
        reward = self._reward_service.get_reward(reward_id)
        if not reward:
            return
        if reward.status != "available":
            QMessageBox.information(self, "Premio no disponible", "Este premio ya no está disponible.")
            return
        dialog = RewardRedeemDialog(reward, self._reward_service, self)
        if dialog.exec():
            self.refresh()
            self._on_changed(reward.customer_id)

    @staticmethod
    def _fill_row(table: QTableWidget, row: int, values: list[str]) -> None:
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))
