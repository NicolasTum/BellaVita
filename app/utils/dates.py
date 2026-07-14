from __future__ import annotations

from datetime import date


MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def format_birth_date(value: str | None) -> str:
    parsed = parse_iso_date(value)
    if not parsed:
        return "No informada"
    return parsed.strftime("%d/%m/%Y")


def birthday_month_name(value: str | None) -> str:
    parsed = parse_iso_date(value)
    if not parsed:
        return "No informado"
    return MONTH_NAMES[parsed.month]
