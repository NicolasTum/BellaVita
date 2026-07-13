from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import SETTINGS


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{SETTINGS.app_name} {SETTINGS.version}")
        self.setMinimumSize(1024, 680)
        self.setCentralWidget(self._build_content())

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        title = QLabel(SETTINGS.app_name)
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Panel inicial del programa de fidelizacion")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        search_button = QPushButton("Buscar cliente")
        new_customer_button = QPushButton("Nuevo cliente")
        purchase_button = QPushButton("Registrar compra")

        for button in (search_button, new_customer_button, purchase_button):
            button.setMinimumHeight(48)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(search_button)
        layout.addWidget(new_customer_button)
        layout.addWidget(purchase_button)
        layout.addStretch(2)

        container.setStyleSheet(
            """
            QWidget {
                background: #f7f4ef;
                color: #252525;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 15px;
            }
            QLabel#Title {
                font-size: 34px;
                font-weight: 700;
            }
            QLabel#Subtitle {
                color: #67615a;
                font-size: 17px;
            }
            QPushButton {
                background: #2f6f73;
                color: white;
                border: 0;
                border-radius: 8px;
                padding: 12px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #285f63;
            }
            QPushButton:pressed {
                background: #214f52;
            }
            """
        )

        return container
