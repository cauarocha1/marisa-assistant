"""Testes da política de validade e ambiguidade da grade."""

from datetime import date, time

from agent.schedule import deduce_class_time


def test_deduce_class_time_for_unique_discipline_on_day() -> None:
    assert deduce_class_time(date(2026, 8, 3), "Introdução à POO") == (
        time(19, 0),
        time(20, 40),
    )


def test_deduce_class_time_outside_validity_requires_confirmation() -> None:
    assert deduce_class_time(date(2027, 8, 2), "Introdução à POO") is None


def test_deduce_class_time_for_multiple_day_discipline_without_match_requires_confirmation() -> None:
    assert deduce_class_time(date(2026, 8, 3), "Matemática Discreta") is None

