from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import SETTINGS
from app.repositories.customers import CustomerRecord
from app.repositories.dashboard import DashboardRepository
from app.repositories.history import CustomerHistoryRepository
from app.repositories.loyalty import LoyaltyRepository
from app.services.backups import BackupError, BackupService
from app.services.customers import CustomerService
from app.services.purchases import PurchaseService
from app.services.rewards import RewardService
from app.services.settings import SettingsService
from app.ui.branding import app_icon, logo_label
from app.ui.backups_page import BackupsPage
from app.ui.customer_history_page import CustomerHistoryPage
from app.ui.customer_dialog import CustomerDialog
from app.ui.loyalty_card_page import LoyaltyCardPage
from app.ui.purchase_page import PurchasePage
from app.ui.rewards_page import RewardsPage
from app.ui.settings_page import SettingsPage
from app.utils.money import format_money, money_from_db
from app.utils.paths import database_path, resource_path


def _font_family() -> str:
    if sys.platform == "win32":
        return '"Segoe UI", Arial, sans-serif'
    if sys.platform == "darwin":
        return '"Helvetica Neue", Arial, sans-serif'
    return "Arial, sans-serif"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._customer_service = CustomerService(database_path())
        self._settings_service = SettingsService(database_path())
        self._purchase_service = PurchaseService(database_path(), self._settings_service)
        self._reward_service = RewardService(database_path())
        self._backup_service = BackupService(database_path())
        self._loyalty_repository = LoyaltyRepository(database_path())
        self._history_repository = CustomerHistoryRepository(database_path())
        self._dashboard_repository = DashboardRepository(database_path())
        self._selected_customer_id: int | None = None
        self._current_customers: list[CustomerRecord] = []

        self.setWindowTitle(f"{SETTINGS.app_name} {SETTINGS.version}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1100, 720)

        self.stack = QStackedWidget()
        self.home_page = self._build_home_page()
        self.customer_search_page = self._build_customer_search_page()
        self.customer_detail_page = self._build_customer_detail_page()
        self.purchase_page = PurchasePage(
            self._customer_service,
            self._purchase_service,
            self._show_home,
            self._after_purchase_saved,
        )
        self.loyalty_card_page = LoyaltyCardPage(
            self._customer_service,
            self._loyalty_repository,
            self._back_to_current_customer,
            self._show_purchase_for_customer,
        )
        self.rewards_page = RewardsPage(
            self._reward_service,
            self._show_home,
            self._after_reward_changed,
        )
        self.customer_history_page = CustomerHistoryPage(
            self._customer_service,
            self._history_repository,
            self._reward_service,
            self._back_to_current_customer,
            self._show_purchase_for_customer,
            self._after_reward_changed,
        )
        self.settings_page = SettingsPage(
            self._settings_service,
            self._show_home,
            self._after_settings_saved,
        )
        self.backups_page = BackupsPage(
            self._backup_service,
            self._show_home,
        )
        self.placeholder_page = self._build_placeholder_page()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.customer_search_page)
        self.stack.addWidget(self.customer_detail_page)
        self.stack.addWidget(self.purchase_page)
        self.stack.addWidget(self.loyalty_card_page)
        self.stack.addWidget(self.rewards_page)
        self.stack.addWidget(self.customer_history_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.backups_page)
        self.stack.addWidget(self.placeholder_page)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.stack)
        root.setStyleSheet(self._stylesheet())
        self.setCentralWidget(root)
        self._refresh_dashboard()

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        brand_header = self._brand_header()

        self.dashboard_label = QLabel()
        self.dashboard_label.setObjectName("DetailInfo")
        self.dashboard_label.setAlignment(Qt.AlignCenter)
        self.dashboard_label.setWordWrap(True)

        buttons = [
            ("Buscar cliente", self._show_customer_search),
            ("Nuevo cliente", self._open_new_customer),
            ("Registrar compra", self._show_purchase_page),
            ("Premios disponibles", self._show_rewards_page),
            ("Crear copia de seguridad", self._show_backups_page),
        ]
        if self._settings_service.can_open_settings():
            buttons.append(("Configuración", self._show_settings_page))

        grid = QGridLayout()
        grid.setSpacing(14)
        for index, (label, slot) in enumerate(buttons):
            button = QPushButton(label)
            button.setMinimumHeight(52)
            button.clicked.connect(slot)
            grid.addWidget(button, index // 2, index % 2)

        footer = QLabel(f"Bella Vita · Club de Compras · Versión {SETTINGS.version}\nUso interno")
        footer.setObjectName("FooterText")
        footer.setAlignment(Qt.AlignCenter)

        layout.addWidget(brand_header)
        layout.addSpacing(12)
        layout.addWidget(self.dashboard_label)
        layout.addSpacing(20)
        layout.addLayout(grid)
        layout.addStretch(2)
        layout.addWidget(footer)
        return page

    def _brand_header(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(22)

        logo_card = QFrame()
        logo_card.setObjectName("BrandLogoCard")
        logo_layout = QHBoxLayout(logo_card)
        logo_layout.setContentsMargins(18, 14, 18, 14)
        logo_layout.addWidget(logo_label(100))

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        brand_name = QLabel("Bella Vita")
        brand_name.setObjectName("BrandName")
        brand_subtitle = QLabel("Club de Compras")
        brand_subtitle.setObjectName("BrandSubtitle")

        text_layout.addStretch(1)
        text_layout.addWidget(brand_name)
        text_layout.addWidget(brand_subtitle)
        text_layout.addStretch(1)

        layout.addWidget(logo_card)
        layout.addLayout(text_layout)
        layout.addStretch(1)
        return container

    def _build_customer_search_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        header = self._header("Clientes", "Buscar, crear y abrir la ficha completa de clientes.")
        actions = QHBoxLayout()
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._show_home)
        new_button = QPushButton("Nuevo cliente")
        new_button.clicked.connect(self._open_new_customer)
        actions.addWidget(back_button)
        actions.addStretch(1)
        actions.addWidget(new_button)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, apellido, telefono, correo o ID")
        self.search_input.textChanged.connect(self._refresh_customer_table)

        self.customer_table = QTableWidget(0, 7)
        self.customer_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Cliente",
                "Telefono",
                "Correo",
                "Stickers",
                "Premios",
                "Estado",
            ]
        )
        self.customer_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.customer_table.doubleClicked.connect(self._open_selected_customer)

        open_button = QPushButton("Abrir ficha")
        open_button.clicked.connect(self._open_selected_customer)

        layout.addWidget(header)
        layout.addLayout(actions)
        layout.addWidget(self.search_input)
        layout.addWidget(self.customer_table)
        layout.addWidget(open_button)
        return page

    def _build_customer_detail_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        self.detail_title = self._header("Ficha de cliente", "")
        self.detail_info = QLabel()
        self.detail_info.setObjectName("DetailInfo")
        self.detail_info.setWordWrap(True)

        actions = QHBoxLayout()
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._show_customer_search)
        edit_button = QPushButton("Editar cliente")
        edit_button.clicked.connect(self._edit_current_customer)
        self.toggle_active_button = QPushButton("Desactivar cliente")
        self.toggle_active_button.clicked.connect(self._toggle_current_customer)
        history_button = QPushButton("Ver historial")
        history_button.clicked.connect(self._show_history_for_current_customer)
        cycle_button = QPushButton("Ciclo actual")
        cycle_button.clicked.connect(self._show_loyalty_card_for_current_customer)
        rewards_button = QPushButton("Premios disponibles")
        rewards_button.clicked.connect(self._show_rewards_for_current_customer)

        for button in (
            back_button,
            edit_button,
            self.toggle_active_button,
            history_button,
            cycle_button,
            rewards_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)

        layout.addWidget(self.detail_title)
        layout.addWidget(self.detail_info)
        layout.addLayout(actions)
        layout.addStretch(1)
        return page

    def _build_placeholder_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        self.placeholder_title = QLabel()
        self.placeholder_title.setObjectName("Title")
        self.placeholder_title.setAlignment(Qt.AlignCenter)
        self.placeholder_text = QLabel()
        self.placeholder_text.setObjectName("Subtitle")
        self.placeholder_text.setAlignment(Qt.AlignCenter)
        self.placeholder_text.setWordWrap(True)
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._return_from_placeholder)

        layout.addStretch(1)
        layout.addWidget(self.placeholder_title)
        layout.addWidget(self.placeholder_text)
        layout.addWidget(back_button)
        layout.addStretch(2)
        return page

    def _header(self, title: str, subtitle: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Subtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return container

    def _show_home(self) -> None:
        self._refresh_dashboard()
        self.stack.setCurrentWidget(self.home_page)

    def _refresh_dashboard(self) -> None:
        stats = self._dashboard_repository.stats()
        self.dashboard_label.setText(
            " | ".join(
                [
                    f"Compras hoy: {stats.purchases_today}",
                    f"Premios disponibles: {stats.rewards_available}",
                    f"Valor total de premios disponibles: {format_money(stats.rewards_available_value)}",
                    f"Premios utilizados: {stats.rewards_used}",
                    f"Ciclos a 1 compra: {stats.cycles_near_completion}",
                ]
            )
        )

    def _show_customer_search(self) -> None:
        self._refresh_customer_table()
        self.stack.setCurrentWidget(self.customer_search_page)

    def _open_new_customer(self) -> None:
        dialog = CustomerDialog(self._customer_service, self)
        if dialog.exec() == QDialog.Accepted and dialog.saved_customer_id:
            self.statusBar().showMessage(
                f"Cliente #{dialog.saved_customer_id} creado correctamente",
                6000,
            )
            self._refresh_customer_table()
            self._show_customer_detail(dialog.saved_customer_id)

    def _refresh_customer_table(self) -> None:
        term = self.search_input.text() if hasattr(self, "search_input") else ""
        self._current_customers = self._customer_service.search_customers(term)
        self.customer_table.setRowCount(len(self._current_customers))
        for row_index, customer in enumerate(self._current_customers):
            values = [
                str(customer.id),
                customer.full_name,
                customer.phone or "",
                customer.email or "",
                f"{customer.current_stickers}/{customer.current_cycle_target}",
                str(customer.available_rewards),
                "Activo" if customer.is_active else "Inactivo",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(Qt.UserRole, customer.id)
                self.customer_table.setItem(row_index, column_index, item)

    def _open_selected_customer(self) -> None:
        selected = self.customer_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Seleccionar cliente", "Seleccioná un cliente de la lista.")
            return
        customer_id = int(self.customer_table.item(selected[0].row(), 0).text())
        self._show_customer_detail(customer_id)

    def _show_customer_detail(self, customer_id: int) -> None:
        customer = self._customer_service.get_customer(customer_id)
        if not customer:
            QMessageBox.warning(self, "Cliente no encontrado", "No se pudo abrir la ficha del cliente.")
            self._show_customer_search()
            return

        self._selected_customer_id = customer.id
        self.detail_title.findChild(QLabel, "SectionTitle").setText(customer.full_name)
        self.detail_title.findChildren(QLabel)[1].setText(f"Cliente #{customer.id}")
        self.detail_info.setText(
            "\n".join(
                [
                    f"Telefono: {customer.phone or '-'}",
                    f"Correo: {customer.email or '-'}",
                    f"Estado: {'Activo' if customer.is_active else 'Inactivo'}",
                    f"Consentimiento promociones: {'Si' if customer.marketing_consent else 'No'}",
                    f"Alta: {customer.created_at}",
                    f"Stickers del ciclo actual: {customer.current_stickers}/{customer.current_cycle_target}",
                    f"Total del ciclo actual: {format_money(money_from_db(customer.current_cycle_total))}",
                    f"Promedio parcial: {format_money(money_from_db(customer.current_cycle_average))}",
                    f"Compras faltantes: {max(0, customer.current_cycle_target - customer.current_stickers)}",
                    f"Ciclos completados: {customer.completed_cycles}",
                    f"Premios disponibles: {customer.available_rewards}",
                    f"Ultima compra: {customer.last_purchase_at or '-'}",
                    f"Observaciones: {customer.notes or '-'}",
                ]
            )
        )
        self.toggle_active_button.setText(
            "Desactivar cliente" if customer.is_active else "Activar cliente"
        )
        self.stack.setCurrentWidget(self.customer_detail_page)

    def _show_purchase_page(self) -> None:
        self.purchase_page.refresh()
        self.stack.setCurrentWidget(self.purchase_page)
        self._run_automatic_backup("purchase_saved")

    def _show_purchase_for_customer(self, customer_id: int) -> None:
        self.purchase_page.preselect_customer(customer_id)
        self.stack.setCurrentWidget(self.purchase_page)

    def _after_purchase_saved(self, result) -> None:
        self._refresh_customer_table()
        self._refresh_dashboard()
        self._selected_customer_id = result.customer_id
        if self.stack.currentWidget() is self.loyalty_card_page:
            self.loyalty_card_page.refresh()
        self.purchase_page.refresh()
        self.stack.setCurrentWidget(self.purchase_page)

    def _show_loyalty_card_for_current_customer(self) -> None:
        if self._selected_customer_id is None:
            QMessageBox.information(self, "Seleccionar cliente", "Abrí primero la ficha de un cliente.")
            return
        self.loyalty_card_page.show_customer(self._selected_customer_id)
        self.stack.setCurrentWidget(self.loyalty_card_page)

    def _show_rewards_page(self) -> None:
        self.rewards_page.refresh()
        self.stack.setCurrentWidget(self.rewards_page)

    def _show_backups_page(self) -> None:
        self.backups_page.refresh()
        self.stack.setCurrentWidget(self.backups_page)

    def _show_settings_page(self) -> None:
        if not self._settings_service.can_open_settings():
            QMessageBox.warning(self, "Acceso denegado", "Solo un administrador puede abrir configuración.")
            return
        self.settings_page.load_settings()
        self.stack.setCurrentWidget(self.settings_page)

    def _after_settings_saved(self) -> None:
        self._refresh_dashboard()
        self.purchase_page.refresh()
        self._run_automatic_backup("settings_saved")

    def _show_rewards_for_current_customer(self) -> None:
        if self._selected_customer_id is None:
            return
        customer = self._customer_service.get_customer(self._selected_customer_id)
        self.rewards_page.search_input.setText(customer.full_name if customer else "")
        self.rewards_page.status_input.setCurrentIndex(1)
        self.rewards_page.refresh()
        self.stack.setCurrentWidget(self.rewards_page)

    def _show_history_for_current_customer(self) -> None:
        if self._selected_customer_id is None:
            QMessageBox.information(self, "Seleccionar cliente", "Abrí primero la ficha de un cliente.")
            return
        self.customer_history_page.show_customer(self._selected_customer_id)
        self.stack.setCurrentWidget(self.customer_history_page)

    def _after_reward_changed(self, customer_id: int) -> None:
        self._refresh_dashboard()
        self._refresh_customer_table()
        if self._selected_customer_id == customer_id:
            self._show_customer_detail(customer_id)
        self._run_automatic_backup("reward_changed")

    def _back_to_current_customer(self) -> None:
        if self._selected_customer_id is not None:
            self._show_customer_detail(self._selected_customer_id)
        else:
            self._show_customer_search()

    def _edit_current_customer(self) -> None:
        if self._selected_customer_id is None:
            return
        customer = self._customer_service.get_customer(self._selected_customer_id)
        if not customer:
            QMessageBox.warning(self, "Cliente no encontrado", "No se pudo editar el cliente.")
            return
        dialog = CustomerDialog(self._customer_service, self, customer=customer)
        if dialog.exec() == QDialog.Accepted:
            self.statusBar().showMessage("Cliente actualizado correctamente", 6000)
            self._refresh_customer_table()
            self._show_customer_detail(customer.id)

    def _toggle_current_customer(self) -> None:
        if self._selected_customer_id is None:
            return
        customer = self._customer_service.get_customer(self._selected_customer_id)
        if not customer:
            return
        target_state = not customer.is_active
        action = "activar" if target_state else "desactivar"
        answer = QMessageBox.question(
            self,
            "Confirmar cambio",
            f"¿Querés {action} a {customer.full_name}?",
        )
        if answer != QMessageBox.Yes:
            return
        self.toggle_active_button.setEnabled(False)
        try:
            self._customer_service.set_customer_active(customer.id, target_state)
        finally:
            self.toggle_active_button.setEnabled(True)
        self.statusBar().showMessage("Estado del cliente actualizado", 6000)
        self._refresh_customer_table()
        self._show_customer_detail(customer.id)

    def _show_placeholder(self, title: str, phase: str) -> None:
        self.placeholder_title.setText(title)
        self.placeholder_text.setText(
            f"Pantalla planificada para {phase}. La navegacion ya esta conectada; "
            "la persistencia especifica se implementara en la fase correspondiente."
        )
        self._previous_page = self.stack.currentWidget()
        self.stack.setCurrentWidget(self.placeholder_page)

    def _return_from_placeholder(self) -> None:
        previous = getattr(self, "_previous_page", self.home_page)
        self.stack.setCurrentWidget(previous)

    def _run_automatic_backup(self, reason: str) -> None:
        try:
            self._backup_service.create_automatic_backup(reason)
        except BackupError as exc:
            self.statusBar().showMessage(f"No se pudo crear respaldo automático: {exc}", 8000)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._run_automatic_backup("app_close")
        super().closeEvent(event)

    def _stylesheet(self) -> str:
        check_icon = resource_path("assets", "icons", "check_white.svg").as_posix()
        return (
            """
            QWidget {
                background: #f7f4ef;
                color: #252525;
                font-family: %s;
                font-size: 15px;
            }
            QLabel#Title {
                font-size: 34px;
                font-weight: 700;
            }
            QFrame#BrandLogoCard {
                background: #ffffff;
                border: 1px solid #ded8ce;
                border-radius: 8px;
            }
            QLabel#BrandName {
                color: #252525;
                font-size: 36px;
                font-weight: 700;
            }
            QLabel#BrandSubtitle {
                color: #214f52;
                font-size: 22px;
                font-weight: 600;
            }
            QLabel#SectionTitle {
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#Subtitle {
                color: #67615a;
                font-size: 16px;
            }
            QLabel#DetailInfo {
                background: #ffffff;
                border: 1px solid #ded8ce;
                border-radius: 8px;
                padding: 18px;
                line-height: 1.45;
            }
            QFrame#SidePanel, QFrame#InfoCard {
                background: #ffffff;
                border: 1px solid #ded8ce;
                border-radius: 8px;
            }
            QLabel#CardTitle {
                font-size: 18px;
                font-weight: 700;
                color: #252525;
            }
            QLabel#SelectedCustomerName {
                font-size: 22px;
                font-weight: 700;
                color: #2f6f73;
            }
            QLabel#DetailText {
                color: #3d3934;
                line-height: 1.35;
            }
            QLabel#Hint {
                color: #67615a;
                font-size: 13px;
            }
            QLabel#FooterText {
                color: #8a837a;
                font-size: 12px;
            }
            QCheckBox {
                spacing: 8px;
                color: #252525;
                min-height: 24px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #4f5d5d;
                border-radius: 5px;
                background: #ffffff;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #2f6f73;
                background: #fbfaf7;
            }
            QCheckBox::indicator:focus {
                border: 2px solid #214f52;
            }
            QCheckBox::indicator:checked {
                background: #2f6f73;
                border: 2px solid #214f52;
                image: url("%s");
            }
            QCheckBox::indicator:checked:hover {
                background: #285f63;
            }
            QLabel#TotalLabel {
                color: #214f52;
                font-size: 24px;
                font-weight: 700;
            }
            QScrollArea#PurchaseScroll {
                border: 0;
                background: transparent;
            }
            QTableWidget {
                gridline-color: #e5ded5;
                selection-background-color: #cfe5df;
                selection-color: #1f3839;
                alternate-background-color: #fbfaf7;
            }
            QTabWidget::pane {
                border: 1px solid #ded8ce;
                background: #ffffff;
                border-radius: 6px;
            }
            QLabel#Sticker {
                background: #ffffff;
                border: 2px dashed #bfb6aa;
                border-radius: 8px;
                padding: 10px;
                color: #67615a;
            }
            QLabel#Sticker[complete="true"] {
                background: #dceee8;
                border: 2px solid #2f6f73;
                color: #214f52;
                font-weight: 700;
            }
            QLineEdit, QTextEdit, QTableWidget, QSpinBox {
                background: #ffffff;
                color: #252525;
                border: 1px solid #d8d1c8;
                border-radius: 6px;
                padding: 8px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #e8e1d7;
                border: 1px solid #b9afa3;
                width: 22px;
            }
            QPushButton {
                background: #2f6f73;
                color: white;
                border: 0;
                border-radius: 8px;
                padding: 11px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #285f63;
            }
            QPushButton:pressed {
                background: #214f52;
            }
            QPushButton:disabled {
                background: #9aa4a5;
            }
            """
            % (_font_family(), check_icon)
        )
