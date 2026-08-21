"""Dedução pura de horários da grade vigente da Marisa."""

from datetime import date, time

_VALID_FROM = date(2026, 8, 1)
_VALID_UNTIL = date(2026, 12, 19)
_WEEKLY_SCHEDULE: dict[int, tuple[tuple[str, time, time], ...]] = {
    0: (
        ("Introdução à POO", time(19, 0), time(20, 40)),
        ("Sistemas de Informação", time(21, 0), time(22, 40)),
    ),
    1: (
        ("Administração Estratégica", time(19, 0), time(20, 40)),
        ("Matemática Discreta", time(21, 0), time(22, 40)),
    ),
    2: (
        ("Introdução à POO", time(19, 0), time(20, 40)),
        ("Estatística Aplicada", time(21, 0), time(22, 40)),
    ),
    3: (
        ("Estatística Aplicada", time(19, 0), time(20, 40)),
        ("Matemática Discreta", time(21, 0), time(22, 40)),
    ),
    4: (("Administração Estratégica", time(19, 0), time(20, 40)),),
}


def deduce_class_time(
    event_date: date, discipline: str
) -> tuple[time, time] | None:
    """Retorna o horário inequívoco da disciplina ou ``None`` para confirmação."""

    if not _VALID_FROM <= event_date <= _VALID_UNTIL:
        return None

    matches = [
        (start, end)
        for scheduled_discipline, start, end in _WEEKLY_SCHEDULE.get(
            event_date.weekday(), ()
        )
        if scheduled_discipline == discipline
    ]
    if len(matches) != 1:
        return None
    return matches[0]
