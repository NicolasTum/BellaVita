from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.csv_import import CsvImportService
from app.services.settings import SettingsPermissionError, SettingsService, SettingsValidationError
from app.ui.csv_import_page import CsvImportPage


class SettingsPage(QWidget):
    def __init__(self, settings_service: SettingsService, on_back, on_saved, parent=None) -> None:
        super().__init__(parent)
        self._settings_service = settings_service
        self._on_back = on_back
        self._on_saved = on_saved
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Configuración")
        title.setObjectName("SectionTitle")
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._on_back)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(back_button)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._promotion_tab(), "Promoción")
        self.tabs.addTab(self._email_tab(), "Correo de promociones")
        self.tabs.addTab(self._store_tab(), "Datos generales")
        self.csv_import_page = CsvImportPage(
            CsvImportService(
                self._settings_service.database_path(),
                self._settings_service.current_user(),
            )
        )
        self.tabs.addTab(self.csv_import_page, "Importar clientes")

        actions = QHBoxLayout()
        save_button = QPushButton("Guardar cambios")
        save_button.clicked.connect(self._save)
        discard_button = QPushButton("Descartar cambios")
        discard_button.clicked.connect(self.load_settings)
        restore_button = QPushButton("Restaurar valores de la sección")
        restore_button.clicked.connect(self._restore_section_defaults)
        actions.addWidget(save_button)
        actions.addWidget(discard_button)
        actions.addWidget(restore_button)
        actions.addStretch(1)

        layout.addLayout(header)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(actions)
        self.load_settings()

    def _promotion_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.target_input = QSpinBox()
        self.target_input.setObjectName("LoyaltyTargetInput")
        self.target_input.setRange(1, 50)
        self.target_input.setValue(6)
        self.target_input.setFixedWidth(120)
        self.target_input.valueChanged.connect(self._update_target_hint)
        self.target_input.setStyleSheet(
            """
            QSpinBox#LoyaltyTargetInput {
                background: #ffffff;
                color: #252525;
                border: 1px solid #b9afa3;
                border-radius: 6px;
                padding: 8px 28px 8px 10px;
                font-size: 16px;
                font-weight: 700;
            }
            QSpinBox#LoyaltyTargetInput::up-button,
            QSpinBox#LoyaltyTargetInput::down-button {
                background: #e8e1d7;
                border: 1px solid #b9afa3;
                width: 24px;
            }
            QSpinBox#LoyaltyTargetInput::up-button:hover,
            QSpinBox#LoyaltyTargetInput::down-button:hover {
                background: #d8eee6;
            }
            """
        )
        self.target_help = QLabel(
            "Cada compra agrega un cupón. Al completar esta cantidad, se calcula el "
            "promedio de las compras y se genera el premio."
        )
        self.target_help.setObjectName("Hint")
        self.target_help.setWordWrap(True)
        self.target_current_label = QLabel()
        self.target_current_label.setObjectName("Hint")
        self.promotion_name_input = QLineEdit()
        self.promotion_description_input = QTextEdit()
        self.promotion_description_input.setFixedHeight(80)
        self.loyalty_active_input = QCheckBox("Promoción activa")
        self.allow_new_cycle_input = QCheckBox("Permitir ciclo nuevo con premio pendiente")
        target_box = QVBoxLayout()
        target_box.setSpacing(6)
        target_box.addWidget(self.target_input)
        target_box.addWidget(self.target_help)
        target_box.addWidget(self.target_current_label)
        form.addRow("Compras necesarias para obtener el premio", target_box)
        form.addRow("Nombre de la promoción", self.promotion_name_input)
        form.addRow("Texto breve", self.promotion_description_input)
        form.addRow("", self.loyalty_active_input)
        form.addRow("", self.allow_new_cycle_input)
        return page

    def _email_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.sender_name_input = QLineEdit()
        self.sender_email_input = QLineEdit()
        self.reply_to_input = QLineEdit()
        self.default_subject_input = QLineEdit()
        self.default_signature_input = QTextEdit()
        self.default_signature_input.setFixedHeight(100)
        self.email_status_input = QComboBox()
        self.email_status_input.addItem("No configurado", "not_configured")
        self.email_status_input.addItem("Configurado", "configured")
        self.email_status_input.addItem("Deshabilitado", "disabled")
        form.addRow("Nombre remitente", self.sender_name_input)
        form.addRow("Correo remitente", self.sender_email_input)
        form.addRow("Correo de respuesta", self.reply_to_input)
        form.addRow("Asunto predeterminado", self.default_subject_input)
        form.addRow("Firma predeterminada", self.default_signature_input)
        form.addRow("Estado de envío", self.email_status_input)
        return page

    def _store_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.store_name_input = QLineEdit()
        self.store_phone_input = QLineEdit()
        self.store_email_input = QLineEdit()
        self.store_address_input = QLineEdit()
        self.currency_code_input = QLineEdit()
        self.currency_symbol_input = QLineEdit()
        self.legal_text_input = QTextEdit()
        self.legal_text_input.setFixedHeight(80)
        self.marketing_consent_required_input = QCheckBox("Requerir consentimiento promocional")
        form.addRow("Nombre de tienda *", self.store_name_input)
        form.addRow("Teléfono", self.store_phone_input)
        form.addRow("Correo general", self.store_email_input)
        form.addRow("Dirección", self.store_address_input)
        form.addRow("Moneda", self.currency_code_input)
        form.addRow("Símbolo", self.currency_symbol_input)
        form.addRow("Texto legal", self.legal_text_input)
        form.addRow("", self.marketing_consent_required_input)
        return page

    def load_settings(self) -> None:
        values = self._settings_service.get_settings()
        self._loaded_target = int(values["loyalty_target_purchase_count"])
        self.target_input.setValue(self._loaded_target)
        self._update_target_hint()
        self.promotion_name_input.setText(values["promotion_name"])
        self.promotion_description_input.setPlainText(values["promotion_description"])
        self.loyalty_active_input.setChecked(values["loyalty_active"] == "1")
        self.allow_new_cycle_input.setChecked(values["allow_new_cycle_with_pending_reward"] == "1")
        self.sender_name_input.setText(values["promotion_sender_name"])
        self.sender_email_input.setText(values["promotion_sender_email"])
        self.reply_to_input.setText(values["promotion_reply_to_email"])
        self.default_subject_input.setText(values["promotion_default_subject"])
        self.default_signature_input.setPlainText(values["promotion_default_signature"])
        index = self.email_status_input.findData(values["promotion_email_status"])
        self.email_status_input.setCurrentIndex(max(0, index))
        self.store_name_input.setText(values["store_name"])
        self.store_phone_input.setText(values["store_phone"])
        self.store_email_input.setText(values["store_email"])
        self.store_address_input.setText(values["store_address"])
        self.currency_code_input.setText(values["currency_code"])
        self.currency_symbol_input.setText(values["currency_symbol"])
        self.legal_text_input.setPlainText(values["promotion_legal_text"])
        self.marketing_consent_required_input.setChecked(values["marketing_consent_required"] == "1")

    def _save(self) -> None:
        if self.target_input.value() != self._loaded_target:
            answer = QMessageBox.question(
                self,
                "Cambiar cantidad de compras",
                "Este cambio aplicará únicamente a los nuevos ciclos. "
                "Los ciclos existentes conservarán su cantidad objetivo actual.",
            )
            if answer != QMessageBox.Yes:
                return
        try:
            self._settings_service.save_settings(self._values())
        except (SettingsPermissionError, SettingsValidationError) as exc:
            QMessageBox.warning(self, "No se pudo guardar", str(exc))
            return
        QMessageBox.information(self, "Configuración guardada", "Los cambios fueron guardados.")
        self.load_settings()
        self._on_saved()

    def _restore_section_defaults(self) -> None:
        self.load_settings()

    def _update_target_hint(self) -> None:
        if hasattr(self, "target_current_label"):
            self.target_current_label.setText(
                f"Configuración actual: {self.target_input.value()} compras por ciclo"
            )

    def _values(self) -> dict[str, str]:
        return {
            "loyalty_target_purchase_count": str(self.target_input.value()),
            "promotion_name": self.promotion_name_input.text().strip(),
            "promotion_description": self.promotion_description_input.toPlainText().strip(),
            "loyalty_active": "1" if self.loyalty_active_input.isChecked() else "0",
            "allow_new_cycle_with_pending_reward": "1" if self.allow_new_cycle_input.isChecked() else "0",
            "promotion_sender_name": self.sender_name_input.text().strip(),
            "promotion_sender_email": self.sender_email_input.text().strip(),
            "promotion_reply_to_email": self.reply_to_input.text().strip(),
            "promotion_default_subject": self.default_subject_input.text().strip(),
            "promotion_default_signature": self.default_signature_input.toPlainText().strip(),
            "promotion_email_status": self.email_status_input.currentData(),
            "store_name": self.store_name_input.text().strip(),
            "store_phone": self.store_phone_input.text().strip(),
            "store_email": self.store_email_input.text().strip(),
            "store_address": self.store_address_input.text().strip(),
            "currency_code": self.currency_code_input.text().strip(),
            "currency_symbol": self.currency_symbol_input.text().strip(),
            "promotion_legal_text": self.legal_text_input.toPlainText().strip(),
            "marketing_consent_required": "1" if self.marketing_consent_required_input.isChecked() else "0",
        }
