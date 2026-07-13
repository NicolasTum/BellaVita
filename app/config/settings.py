from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "Club de Compras"
    app_id: str = "ClubCompras"
    version: str = "0.1.0"
    currency_symbol: str = "$"
    locale: str = "es_UY"
    stickers_per_cycle: int = 6
    default_backup_retention: int = 30


SETTINGS = AppSettings()
