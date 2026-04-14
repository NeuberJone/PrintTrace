from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Converte valores diversos para float.
    Aceita vírgula decimal e espaços.
    """
    try:
        text = str(value).strip().replace(",", ".")
        if not text:
            return default
        return float(text)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Converte valores diversos para int.
    Passa primeiro por float para tolerar '12.0'.
    """
    try:
        return int(float(str(value).strip().replace(",", ".")))
    except Exception:
        return default


def round_up_2(value: float) -> float:
    """
    Arredonda sempre para cima em 2 casas decimais.
    Ex.: 0.001 -> 0.01
    """
    q = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    return float(q)


def round_up_4(value: float) -> float:
    """
    Arredonda sempre para cima em 4 casas decimais.
    """
    q = Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
    return float(q)


def fmt_num(value: float) -> str:
    """
    Formata número com 2 casas e padrão brasileiro.
    Ex.: 1234.5 -> 1.234,50
    """
    formatted = f"{round_up_2(value):,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_money(value: float) -> str:
    return f"R$ {fmt_num(value)}"


def fmt_m(value: float) -> str:
    return f"{fmt_num(value)} m"


def fmt_m_no_suffix(value: float) -> str:
    return fmt_num(value)


def fmt_m2(value: float) -> str:
    return f"{fmt_num(value)} m²"


def fmt_mm(value: float) -> str:
    return f"{fmt_num(value)} mm"


def fmt_ml(value: float) -> str:
    return f"{fmt_num(value)} mL"


def fmt_l(value: float) -> str:
    return f"{fmt_num(value)} L"


def fmt_pct(value: float) -> str:
    return f"{fmt_num(value)}%"


def fmt_speed(value: float) -> str:
    return f"{fmt_num(value)} m/min"


def fmt_seconds(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}h {minutes:02d}min {seconds:02d}s"


def bytes_to_mb(size_bytes: int) -> float:
    if size_bytes <= 0:
        return 0.0
    return size_bytes / (1024 * 1024)


def fmt_file_size(size_bytes: int) -> str:
    """
    Exibe B, KB ou MB com 2 casas quando necessário.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"

    if size_bytes < 1024 * 1024:
        kb = size_bytes / 1024
        return f"{fmt_num(kb)} KB"

    mb = bytes_to_mb(size_bytes)
    return f"{fmt_num(mb)} MB"