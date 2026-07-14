from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from app.services.birthday_promotions import BirthdayPromotionService
from app.utils.dates import MONTH_NAMES
from app.utils.paths import export_dir


class BirthdaysPage(QWidget):
    def __init__(self, birthday_service: BirthdayPromotionService, on_back, parent=None) -> None:
        super().__init__(parent)
        self._birthday_service = birthday_service
        self._on_back = on_back
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Cumpleaños del mes")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Clientes activos con fecha de nacimiento cargada para campañas del mes.")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
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
        self.consent_input = QCheckBox("Solo clientes con consentimiento promocional")
        self.consent_input.stateChanged.connect(self.refresh)
        export_button = QPushButton("Exportar CSV")
        export_button.clicked.connect(self._export)
        filters.addWidget(QLabel("Mes"))
        filters.addWidget(self.month_input)
        filters.addWidget(self.consent_input)
        filters.addStretch(1)
        filters.addWidget(export_button)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("DetailInfo")

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Cliente",
                "Cumpleaños",
                "Teléfono",
                "Correo",
                "Consentimiento",
                "Última compra",
                "Premios",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        layout.addLayout(header)
        layout.addLayout(filters)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        month = self.month_input.currentData()
        require_consent = self.consent_input.isChecked()
        customers = self._birthday_service.customers_for_month(
            month,
            require_marketing_consent=require_consent,
            require_contact=require_consent,
        )
        self.summary_label.setText(
            f"{len(customers)} cliente(s) activos con cumpleaños en {MONTH_NAMES[month]}."
        )
        self.table.setRowCount(len(customers))
        for row, customer in enumerate(customers):
            values = [
                f"{customer.first_name} {customer.last_name}",
                f"{customer.birthday_day:02d}/{customer.birthday_month:02d}",
                customer.phone or "",
                customer.email or "",
                "Si" if customer.marketing_consent else "No",
                customer.last_purchase_at or "",
                str(customer.available_rewards),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

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
        path = self._birthday_service.export_month(
            month,
            destination=Path(file_name),
            require_marketing_consent=self.consent_input.isChecked(),
        )
        QMessageBox.information(self, "Exportación creada", f"Archivo generado:\n{path}")
