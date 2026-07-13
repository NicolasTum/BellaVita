from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from app.repositories.customers import CustomerRecord
from app.services.customers import CustomerService, CustomerValidationError


class CustomerDialog(QDialog):
    def __init__(
        self,
        customer_service: CustomerService,
        parent=None,
        customer: CustomerRecord | None = None,
    ) -> None:
        super().__init__(parent)
        self._customer_service = customer_service
        self._customer = customer
        self.created_customer_id: int | None = None
        self.saved_customer_id: int | None = customer.id if customer else None
        self.setWindowTitle("Editar cliente" if customer else "Nuevo cliente")
        self.setMinimumWidth(520)
        self._build_ui()
        if self._customer:
            self._load_customer(self._customer)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(90)
        self.marketing_consent_input = QCheckBox("Acepta recibir promociones")

        form.addRow("Nombre *", self.first_name_input)
        form.addRow("Apellido *", self.last_name_input)
        form.addRow("Telefono", self.phone_input)
        form.addRow("Correo", self.email_input)
        form.addRow("Observaciones", self.notes_input)
        form.addRow("", self.marketing_consent_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText(
            "Guardar cambios" if self._customer else "Guardar cliente"
        )
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def _load_customer(self, customer: CustomerRecord) -> None:
        self.first_name_input.setText(customer.first_name)
        self.last_name_input.setText(customer.last_name)
        self.phone_input.setText(customer.phone or "")
        self.email_input.setText(customer.email or "")
        self.notes_input.setPlainText(customer.notes or "")
        self.marketing_consent_input.setChecked(customer.marketing_consent)

    def _save(self) -> None:
        try:
            customer = self._customer_service.build_customer(
                first_name=self.first_name_input.text(),
                last_name=self.last_name_input.text(),
                phone=self.phone_input.text(),
                email=self.email_input.text(),
                notes=self.notes_input.toPlainText(),
                marketing_consent=self.marketing_consent_input.isChecked(),
            )
        except CustomerValidationError as exc:
            QMessageBox.warning(self, "Revisar datos", str(exc))
            return

        duplicates = [
            item
            for item in self._customer_service.find_possible_duplicates(customer)
            if not self._customer or item.id != self._customer.id
        ]
        if duplicates:
            details = "\n".join(
                f"- {item.first_name} {item.last_name} ({item.reason})"
                for item in duplicates[:5]
            )
            answer = QMessageBox.question(
                self,
                "Posible cliente duplicado",
                "Encontré posibles coincidencias:\n\n"
                f"{details}\n\n¿Querés guardar este cliente de todos modos?",
            )
            if answer != QMessageBox.Yes:
                return

        self.buttons.button(QDialogButtonBox.Save).setEnabled(False)
        try:
            if self._customer:
                self._customer_service.update_customer(self._customer.id, customer)
                self.saved_customer_id = self._customer.id
            else:
                result = self._customer_service.create_customer(customer)
                self.created_customer_id = result.customer_id
                self.saved_customer_id = result.customer_id
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.buttons.button(QDialogButtonBox.Save).setEnabled(True)
            QMessageBox.critical(
                self,
                "No se pudo guardar",
                "No se pudo crear el cliente. Revisá los datos e intentá nuevamente.",
            )
            raise exc

        QMessageBox.information(self, "Cliente guardado", "El cliente fue guardado correctamente.")
        self.accept()
