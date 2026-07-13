from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.repositories.rewards import RewardRecord
from app.services.rewards import RewardService, RewardValidationError
from app.utils.money import format_money, to_decimal


class RewardDetailDialog(QDialog):
    def __init__(self, reward: RewardRecord, reward_service: RewardService, parent=None) -> None:
        super().__init__(parent)
        self._reward = reward
        self._reward_service = reward_service
        self.redeemed = False
        self.setWindowTitle(f"Premio #{reward.id}")
        self.setMinimumWidth(560)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel(f"Premio #{self._reward.id} - {self._reward.customer_name}")
        title.setObjectName("SectionTitle")
        details = QLabel(
            "\n".join(
                [
                    f"Cliente: {self._reward.customer_name}",
                    f"Telefono: {self._reward.phone or '-'}",
                    f"Correo: {self._reward.email or '-'}",
                    f"Ciclo: {self._reward.cycle_number}",
                    f"Fecha de generacion: {self._reward.earned_at}",
                    f"Valor del premio: {format_money(self._reward.max_value)}",
                    "Este valor corresponde al promedio de "
                    f"las {self._reward.target_purchase_count} compras realizadas en el ciclo.",
                    f"Estado: {self._reward.status.upper()}",
                    f"Fecha de uso: {self._reward.used_at or '-'}",
                    f"Prenda entregada: {self._reward.delivered_item_description or '-'}",
                    f"Precio de la prenda: {format_money(self._reward.delivered_item_price) if self._reward.delivered_item_price is not None else '-'}",
                    f"Diferencia a pagar: {format_money(self._reward.value_difference) if self._reward.value_difference is not None else '-'}",
                    f"Observaciones: {self._reward.notes or '-'}",
                    f"Usuario entrega: {self._reward.delivered_by_user_id or '-'}",
                    f"Creado: {self._reward.created_at}",
                    f"Actualizado: {self._reward.updated_at}",
                ]
            )
        )
        details.setObjectName("DetailInfo")
        details.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("Volver")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        if self._reward.status == "available":
            redeem_button = QPushButton("Canjear premio")
            redeem_button.clicked.connect(self._redeem)
            buttons.addButton(redeem_button, QDialogButtonBox.ActionRole)

        layout.addWidget(title)
        layout.addWidget(details)
        layout.addWidget(buttons)

    def _redeem(self) -> None:
        dialog = RewardRedeemDialog(self._reward, self._reward_service, self)
        if dialog.exec() == QDialog.Accepted:
            self.redeemed = True
            self.accept()


class RewardRedeemDialog(QDialog):
    def __init__(self, reward: RewardRecord, reward_service: RewardService, parent=None) -> None:
        super().__init__(parent)
        self._reward = reward
        self._reward_service = reward_service
        self.setWindowTitle(f"Canjear premio #{reward.id}")
        self.setMinimumWidth(520)
        self._saving = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.customer_label = QLabel(self._reward.customer_name)
        self.reward_value_label = QLabel(format_money(self._reward.max_value))
        self.available_credit_label = QLabel(format_money(self._reward.max_value))
        self.item_input = QLineEdit()
        self.price_input = QLineEdit()
        self.difference_input = QLineEdit("0")
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        self.warning_label = QLabel("")
        self.warning_label.setObjectName("Hint")
        self.price_input.textChanged.connect(self._suggest_difference)

        form.addRow("Cliente", self.customer_label)
        form.addRow("Valor del premio", self.reward_value_label)
        form.addRow("Crédito disponible para la prenda", self.available_credit_label)
        form.addRow("Prenda entregada *", self.item_input)
        form.addRow("Precio de la prenda elegida *", self.price_input)
        form.addRow("Diferencia a pagar", self.difference_input)
        form.addRow("Observaciones", self.notes_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText("Confirmar canje")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(self.warning_label)
        layout.addWidget(self.buttons)

    def _suggest_difference(self) -> None:
        try:
            price = to_decimal(self.price_input.text())
        except ValueError:
            self.warning_label.setText("")
            return
        required = max(Decimal("0.00"), price - self._reward.max_value)
        if required > 0:
            self.warning_label.setText(
                "El precio de la prenda supera el valor del premio. "
                f"El cliente debe abonar una diferencia de {format_money(required)}."
            )
            if not self.difference_input.text().strip() or self.difference_input.text().strip() == "0":
                self.difference_input.setText(str(required))
        else:
            self.warning_label.setText("")
            if not self.difference_input.text().strip():
                self.difference_input.setText("0")

    def _save(self) -> None:
        if self._saving:
            return
        try:
            data = self._reward_service.build_redeem_input(
                reward_id=self._reward.id,
                delivered_item_description=self.item_input.text(),
                delivered_item_price=self.price_input.text(),
                paid_difference=self.difference_input.text(),
                notes=self.notes_input.toPlainText(),
            )
        except RewardValidationError as exc:
            QMessageBox.warning(self, "Revisar canje", str(exc))
            return

        answer = QMessageBox.question(
            self,
            "Confirmar canje",
            f"¿Confirmás canjear el premio de {self._reward.customer_name}?",
        )
        if answer != QMessageBox.Yes:
            return

        self._saving = True
        self.buttons.button(QDialogButtonBox.Save).setEnabled(False)
        try:
            self._reward_service.redeem_reward(data)
        except RewardValidationError as exc:
            QMessageBox.warning(self, "No se pudo canjear", str(exc))
            return
        finally:
            self._saving = False
            self.buttons.button(QDialogButtonBox.Save).setEnabled(True)

        QMessageBox.information(self, "Premio canjeado", "El premio fue marcado como utilizado.")
        self.accept()
