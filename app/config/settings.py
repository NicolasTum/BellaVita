from dataclasses import dataclass

from app.version import VERSION


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "Club de Compras"
    app_id: str = "ClubCompras"
    version: str = VERSION
    currency_symbol: str = "$"
    locale: str = "es_UY"
    stickers_per_cycle: int = 6
    default_backup_retention: int = 30


SETTINGS = AppSettings()
