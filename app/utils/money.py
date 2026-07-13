from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_QUANT = Decimal("0.01")


def to_decimal(value: str | int | Decimal) -> Decimal:
    try:
        amount = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError("Importe invalido.") from exc
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def money_to_db(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def money_from_db(value) -> Decimal:
    return to_decimal(str(value or "0"))


def format_money(value: Decimal) -> str:
    return f"$ {value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)}"
