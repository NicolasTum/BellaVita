from app.config.settings import SETTINGS
from app.database.schema import initialize_database


def test_settings_are_centralized() -> None:
    assert SETTINGS.app_name == "Club de Compras"
    assert SETTINGS.stickers_per_cycle == 6


def test_database_initializes(tmp_path) -> None:
    db_path = tmp_path / "club_compras.db"
    initialize_database(db_path)
    assert db_path.exists()
