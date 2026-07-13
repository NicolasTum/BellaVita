from __future__ import annotations

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
    QVBoxLayout,
    QWidget,
)

from app.repositories.rewards import RewardRecord
from app.services.rewards import RewardService, RewardValidationError
from app.ui.reward_dialogs import RewardDetailDialog, RewardRedeemDialog
from app.utils.money import format_money


STATUS_LABELS = {
    "all": "Todos",
    "available": "Disponible",
    "used": "Utilizado",
    "expired": "Vencido",
    "cancelled": "Anulado",
}


class RewardsPage(QWidget):
    def __init__(self, reward_service: RewardService, on_back, on_changed, parent=None) -> None:
        super().__init__(parent)
        self._reward_service = reward_service
        self._on_back = on_back
        self._on_changed = on_changed
        self._current_rewards: list[RewardRecord] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Premios disponibles")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Buscá premios, abrí su ficha o registrá el canje.")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._on_back)
        header.addLayout(title_box, 1)
        header.addWidget(back_button)

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, apellido, telefono o correo")
        self.search_input.textChanged.connect(self.refresh)
        self.status_input = QComboBox()
        for status, label in STATUS_LABELS.items():
            self.status_input.addItem(label, status)
        self.status_input.setCurrentIndex(1)
        self.status_input.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.search_input, 1)
        filters.addWidget(QLabel("Estado"))
        filters.addWidget(self.status_input)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Cliente", "Ciclo", "Fecha", "Valor del premio", "Estado", "Fecha de canje"]
        )
        self.table.setColumnHidden(0, True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.doubleClicked.connect(self._open_selected_reward)

        actions = QHBoxLayout()
        view_button = QPushButton("Ver premio")
        view_button.clicked.connect(self._open_selected_reward)
        redeem_button = QPushButton("Canjear premio")
        redeem_button.clicked.connect(self._redeem_selected_reward)
        actions.addWidget(view_button)
        actions.addWidget(redeem_button)
        actions.addStretch(1)

        layout.addLayout(header)
        layout.addLayout(filters)
        layout.addWidget(self.table, 1)
        layout.addLayout(actions)

    def refresh(self) -> None:
        status = self.status_input.currentData() if hasattr(self, "status_input") else "available"
        search = self.search_input.text() if hasattr(self, "search_input") else ""
        self._current_rewards = self._reward_service.list_rewards(status=status, search=search)
        self.table.setRowCount(len(self._current_rewards))
        for row_index, reward in enumerate(self._current_rewards):
            values = [
                str(reward.id),
                reward.customer_name,
                str(reward.cycle_number),
                reward.earned_at,
                format_money(reward.max_value),
                STATUS_LABELS.get(reward.status, reward.status),
                reward.used_at or "",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))

    def _selected_reward(self) -> RewardRecord | None:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar premio", "Seleccioná un premio de la lista.")
            return None
        reward_id = int(self.table.item(selected[0].row(), 0).text())
        reward = self._reward_service.get_reward(reward_id)
        if not reward:
            QMessageBox.warning(self, "Premio no encontrado", "No se pudo abrir el premio.")
            self.refresh()
            return None
        return reward

    def _open_selected_reward(self) -> None:
        reward = self._selected_reward()
        if not reward:
            return
        dialog = RewardDetailDialog(reward, self._reward_service, self)
        if dialog.exec() and dialog.redeemed:
            self.refresh()
            self._on_changed(reward.customer_id)

    def _redeem_selected_reward(self) -> None:
        reward = self._selected_reward()
        if not reward:
            return
        if reward.status != "available":
            QMessageBox.information(self, "Premio no disponible", "Este premio ya no se puede canjear.")
            return
        dialog = RewardRedeemDialog(reward, self._reward_service, self)
        if dialog.exec():
            self.refresh()
            self._on_changed(reward.customer_id)
