from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.backups import BackupError, BackupService


class BackupsPage(QWidget):
    def __init__(self, backup_service: BackupService, on_back, parent=None) -> None:
        super().__init__(parent)
        self._backup_service = backup_service
        self._on_back = on_back
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Respaldos")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Crear, revisar y restaurar copias de seguridad de la base local.")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        back_button = QPushButton("Volver")
        back_button.clicked.connect(self._on_back)
        header.addLayout(title_box, 1)
        header.addWidget(back_button)

        status_card = QFrame()
        status_card.setObjectName("InfoCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(18, 18, 18, 18)
        status_layout.setSpacing(8)
        self.database_label = QLabel()
        self.database_label.setObjectName("DetailText")
        self.database_label.setWordWrap(True)
        self.folder_label = QLabel()
        self.folder_label.setObjectName("DetailText")
        self.folder_label.setWordWrap(True)
        self.last_backup_label = QLabel()
        self.last_backup_label.setObjectName("DetailText")
        self.count_label = QLabel()
        self.count_label.setObjectName("DetailText")
        self.state_label = QLabel()
        self.state_label.setObjectName("DetailText")
        status_layout.addWidget(self.database_label)
        status_layout.addWidget(self.folder_label)
        status_layout.addWidget(self.last_backup_label)
        status_layout.addWidget(self.count_label)
        status_layout.addWidget(self.state_label)

        self.backups_table = QTableWidget(0, 3)
        self.backups_table.setHorizontalHeaderLabels(["Fecha", "Tamaño", "Ruta"])
        self.backups_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.backups_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        actions = QHBoxLayout()
        create_button = QPushButton("Crear copia ahora")
        create_button.clicked.connect(self._create_backup)
        choose_button = QPushButton("Elegir carpeta de respaldo")
        choose_button.clicked.connect(self._choose_folder)
        open_button = QPushButton("Abrir carpeta de respaldos")
        open_button.clicked.connect(self._open_folder)
        restore_button = QPushButton("Restaurar copia")
        restore_button.clicked.connect(self._restore_backup)
        actions.addWidget(create_button)
        actions.addWidget(choose_button)
        actions.addWidget(open_button)
        actions.addWidget(restore_button)
        actions.addStretch(1)

        layout.addLayout(header)
        layout.addWidget(status_card)
        layout.addWidget(QLabel("Copias disponibles"))
        layout.addWidget(self.backups_table, 1)
        layout.addLayout(actions)

    def refresh(self) -> None:
        status = self._backup_service.status()
        self.database_label.setText(f"Base SQLite activa: {status.database_path}")
        self.folder_label.setText(f"Carpeta de respaldos: {status.configured_backup_dir}")
        if status.last_success_at:
            self.last_backup_label.setText(
                f"Último respaldo exitoso: {self._format_timestamp(status.last_success_at)}"
            )
        else:
            self.last_backup_label.setText("Aún no se creó ninguna copia de seguridad.")
        self.count_label.setText(f"Copias disponibles: {status.available_count}")
        self.state_label.setText(f"Estado: {status.state}")

        backups = self._backup_service.available_backups()
        self.backups_table.setRowCount(len(backups))
        for row, path in enumerate(backups):
            stat = path.stat()
            values = [
                self._format_file_timestamp(stat.st_mtime),
                self._format_size(stat.st_size),
                str(path),
            ]
            for column, value in enumerate(values):
                self.backups_table.setItem(row, column, QTableWidgetItem(value))

    def _create_backup(self) -> None:
        try:
            result = self._backup_service.create_manual_backup()
        except BackupError as exc:
            QMessageBox.warning(self, "No se pudo crear respaldo", str(exc))
            self.refresh()
            return
        QMessageBox.information(self, "Copia creada", f"{result.message}\n\n{result.path}")
        self.refresh()

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Elegir carpeta de respaldo",
            str(self._backup_service.backup_folder()),
        )
        if not folder:
            return
        self._backup_service.set_backup_folder(Path(folder))
        self.refresh()

    def _open_folder(self) -> None:
        folder = self._backup_service.backup_folder()
        if not folder.exists():
            QMessageBox.warning(self, "Carpeta no disponible", "La carpeta de respaldos no está disponible.")
            self.refresh()
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _restore_backup(self) -> None:
        source = self._selected_backup_path()
        if source is None:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar copia para restaurar",
                str(self._backup_service.backup_folder()),
                "SQLite backups (*.db)",
            )
            if not file_name:
                return
            source = Path(file_name)
        try:
            preview = self._backup_service.preview_restore(source)
        except BackupError as exc:
            QMessageBox.warning(self, "Copia inválida", str(exc))
            return

        answer = QMessageBox.warning(
            self,
            "Restaurar copia",
            "\n".join(
                [
                    "Restaurar una copia reemplazará los datos actuales.",
                    "",
                    f"Fecha del archivo: {preview.created_at.strftime('%d/%m/%Y %H:%M')}",
                    f"Tamaño: {self._format_size(preview.size_bytes)}",
                    f"Ruta: {preview.path}",
                    "",
                    "Antes de restaurar se creará una copia de seguridad de la base actual.",
                ]
            ),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            result = self._backup_service.restore_backup(source)
        except BackupError as exc:
            QMessageBox.warning(self, "No se pudo restaurar", str(exc))
            self.refresh()
            return
        QMessageBox.information(
            self,
            "Copia restaurada",
            "La copia fue restaurada correctamente.\n\n"
            f"Copia previa creada: {result.safety_backup_path}\n\n"
            "Cerrá y abrí nuevamente la aplicación para continuar.",
        )
        self.refresh()

    def _selected_backup_path(self) -> Path | None:
        selected = self.backups_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return Path(self.backups_table.item(row, 2).text())

    @staticmethod
    def _format_timestamp(value: str) -> str:
        date, _, time = value.partition(" ")
        year, month, day = date.split("-")
        hour_minute = time[:5] if time else ""
        return f"{day}/{month}/{year} {hour_minute}".strip()

    @staticmethod
    def _format_file_timestamp(value: float) -> str:
        from datetime import datetime

        return datetime.fromtimestamp(value).strftime("%d/%m/%Y %H:%M")

    @staticmethod
    def _format_size(value: int) -> str:
        if value < 1024:
            return f"{value} B"
        if value < 1024 * 1024:
            return f"{value / 1024:.1f} KB"
        return f"{value / (1024 * 1024):.1f} MB"
