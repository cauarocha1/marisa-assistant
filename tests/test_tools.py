"""Testes de tradução de falhas dos clientes externos das tools."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from agent import memory, tools
from agent.schemas import AddCalendarEventArgs, QueryExpensesArgs, RecordExpenseArgs
from config import get_settings


def _set_required_env(monkeypatch: Any) -> None:
    values = {
        "TELEGRAM_BOT_TOKEN": "telegram-token",
        "TELEGRAM_ADMIN_ID": "123",
        "GEMINI_API_KEY": "gemini-key",
        "GEMINI_MODEL": "gemini-model",
        "SUPABASE_URL": "https://supabase.example.test",
        "SUPABASE_KEY": "supabase-key",
        "CALDAV_URL": "https://calendar.example.test",
        "CALDAV_USERNAME": "user@example.test",
        "APP_SPECIFIC_PASSWORD": "password",
        "CALDAV_CALENDAR_URL": "https://calendar.example.test/cal",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_add_calendar_event_translates_caldav_exception(monkeypatch: Any) -> None:
    _set_required_env(monkeypatch)
    timezone = ZoneInfo("America/Sao_Paulo")
    start = datetime.now(timezone) + timedelta(hours=1)
    monkeypatch.setenv("CALDAV_URL", "https://calendar.example.test")
    monkeypatch.setenv("CALDAV_USERNAME", "user@example.test")
    monkeypatch.setenv("APP_SPECIFIC_PASSWORD", "password")
    monkeypatch.setenv("CALDAV_CALENDAR_URL", "https://calendar.example.test/cal")
    monkeypatch.setattr(
        tools,
        "_caldav_client_factory",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("caldav down")),
    )

    result = tools.add_calendar_event(
        AddCalendarEventArgs(
            summary="Teste",
            start_time=start.isoformat(),
            end_time=(start + timedelta(hours=1)).isoformat(),
        )
    )

    assert not result.ok
    assert result.error_code == "CALDAV_UNAVAILABLE"


def test_record_expense_translates_supabase_exception(monkeypatch: Any) -> None:
    broken_client = type(
        "BrokenClient",
        (),
        {"table": lambda self, name: (_ for _ in ()).throw(RuntimeError("db down"))},
    )()
    monkeypatch.setattr(tools, "_supabase_client", broken_client)

    result = tools.record_expense(
        RecordExpenseArgs(amount=10.0, category="Moradia", sub_category="Casa")
    )

    assert not result.ok
    assert result.error_code == "SUPABASE_UNAVAILABLE"


def test_query_expenses_translates_supabase_exception(monkeypatch: Any) -> None:
    broken_client = type(
        "BrokenClient",
        (),
        {"table": lambda self, name: (_ for _ in ()).throw(RuntimeError("db down"))},
    )()
    monkeypatch.setattr(tools, "_supabase_client", broken_client)

    result = tools.query_expenses(QueryExpensesArgs())

    assert not result.ok
    assert result.error_code == "SUPABASE_UNAVAILABLE"


def test_add_calendar_event_success(monkeypatch: Any) -> None:
    _set_required_env(monkeypatch)
    timezone = ZoneInfo("America/Sao_Paulo")
    start = datetime.now(timezone) + timedelta(hours=1)
    calendar = MagicMock()
    client = MagicMock()
    client.calendar.return_value = calendar
    monkeypatch.setattr(tools, "_caldav_client_factory", lambda **kwargs: client)

    result = tools.add_calendar_event(
        AddCalendarEventArgs(
            summary="Teste",
            start_time=start.isoformat(),
            end_time=(start + timedelta(hours=1)).isoformat(),
        )
    )

    assert result.ok
    calendar.add_event.assert_called_once()


def test_record_expense_success(monkeypatch: Any) -> None:
    _set_required_env(monkeypatch)
    client = MagicMock()
    monkeypatch.setattr(tools, "_supabase_client", client)

    result = tools.record_expense(
        RecordExpenseArgs(
            amount=10.0,
            category="Moradia",
            sub_category="Casa",
            description="Aluguel",
        )
    )

    assert result.ok
    client.table.return_value.insert.return_value.execute.assert_called_once()


def test_query_expenses_success(monkeypatch: Any) -> None:
    _set_required_env(monkeypatch)
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.order.return_value.execute.return_value.data = [
        {"amount": 10, "category": "Moradia"}
    ]
    monkeypatch.setattr(tools, "_supabase_client", client)

    result = tools.query_expenses(QueryExpensesArgs())

    assert result.ok
    assert "Moradia" in result.message


def test_load_recent_history_returns_chronological_messages(monkeypatch: Any) -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"role": "model", "content": "segunda"},
        {"role": "user", "content": "primeira"},
    ]
    monkeypatch.setattr(memory, "_supabase_client", client)

    result = memory.load_recent_history(123)

    assert result == [
        {"role": "user", "content": "primeira"},
        {"role": "model", "content": "segunda"},
    ]


def test_append_message_inserts_and_prunes_old_history(monkeypatch: Any) -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
        {"id": 1}
    ]
    monkeypatch.setattr(memory, "_supabase_client", client)

    memory.append_message(123, "user", "mensagem")

    client.table.return_value.insert.return_value.execute.assert_called_once()
    client.table.return_value.delete.return_value.in_.return_value.execute.assert_called_once_with()
