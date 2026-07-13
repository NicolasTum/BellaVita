from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSplitter

from app.database.schema import initialize_database
from app.services.customers import CustomerService
from app.services.purchases import PurchaseService
from app.ui.purchase_page import PurchasePage


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_purchase_page_uses_two_column_splitter_and_mode_visibility(tmp_path) -> None:
    app = _app()
    db_path = tmp_path / "club.db"
    initialize_database(db_path)
    customer_service = CustomerService(db_path)
    purchase_service = PurchaseService(db_path)

    page = PurchasePage(customer_service, purchase_service, lambda: None, lambda result: None)
    page.resize(1280, 720)
    page.show()
    app.processEvents()

    splitter = page.findChild(QSplitter)
    assert splitter is not None
    assert splitter.count() == 2
    assert page.save_button.isEnabled() is False
    assert page.simple_fields.isVisible() is True
    assert page.detail_fields.isVisible() is False

    page.mode_input.setCurrentText("Detallada")
    app.processEvents()

    assert page.simple_fields.isVisible() is False
    assert page.detail_fields.isVisible() is True
    assert page.items_table.rowCount() >= 1
