"""Testes das funções puras de validação e sanitização."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agent.validation import (
    sanitize_text,
    validate_amount,
    validate_category,
    validate_iso_datetime_range,
)


@pytest.mark.parametrize("value", [-1.0, 0.0, 100_000.0])
def test_validate_amount_rejects_invalid_values(value: float) -> None:
    with pytest.raises(ValueError):
        validate_amount(value)


def test_validate_amount_rounds_to_two_decimal_places() -> None:
    assert validate_amount(12.345) == 12.35


def test_validate_iso_datetime_range_rejects_end_before_or_equal_start() -> None:
    timezone = ZoneInfo("America/Sao_Paulo")
    start = datetime.now(timezone) + timedelta(hours=1)
    with pytest.raises(ValueError):
        validate_iso_datetime_range(start.isoformat(), start.isoformat())


def test_validate_category_rejects_value_outside_enum() -> None:
    with pytest.raises(ValueError):
        validate_category("Categoria inexistente")


def test_sanitize_text_removes_controls_escapes_and_truncates() -> None:
    assert sanitize_text(" A\x00\t B; C, D ", max_length=20) == "A B\\; C\\, D"
    assert sanitize_text("abcdef", max_length=3) == "abc"

