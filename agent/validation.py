"""Validação e sanitização pura dos dados recebidos pelo agente."""

import re
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agent.schemas import EXPENSE_CATEGORIES

_SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def sanitize_text(value: str, *, max_length: int) -> str:
    """
    Remove caracteres de controle, normaliza espaços e escapa iCalendar.

    A quebra de linha (`\\n`) é preservada. O escape da barra invertida é
    aplicado antes dos escapes de ponto e vírgula e vírgula para evitar
    escapar novamente os caracteres inseridos pelo processo.
    """

    if max_length < 0:
        raise ValueError("max_length não pode ser negativo")

    without_controls = "".join(
        character
        for character in value
        if character == "\n" or unicodedata.category(character) != "Cc"
    )
    collapsed = re.sub(r" +", " ", without_controls).strip()
    escaped = collapsed.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    sanitized = escaped[:max_length]

    if not sanitized and max_length > 0:
        raise ValueError("texto vazio após sanitização")

    return sanitized


def validate_amount(value: float) -> float:
    """Valida e arredonda um valor monetário para duas casas decimais."""

    if value <= 0 or value >= 100_000:
        raise ValueError("amount deve ser maior que 0 e menor que 100000")
    return round(value, 2)


def validate_iso_datetime_range(start: str, end: str) -> tuple[datetime, datetime]:
    """Valida um intervalo ISO 8601 e aplica o fuso padrão quando necessário."""

    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except (TypeError, ValueError) as exc:
        raise ValueError("start e end devem ser datas ISO 8601 válidas") from exc

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=_SAO_PAULO_TZ)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=_SAO_PAULO_TZ)

    if end_dt <= start_dt:
        raise ValueError("end deve ser posterior a start")

    now = datetime.now(_SAO_PAULO_TZ)
    if start_dt < now - timedelta(hours=1):
        raise ValueError("start não pode estar mais de uma hora no passado")

    return start_dt, end_dt


def validate_category(value: str) -> str:
    """Valida uma categoria contra o enum definido no schema do projeto."""

    if value not in EXPENSE_CATEGORIES:
        raise ValueError(f"categoria inválida: {value}")
    return value
