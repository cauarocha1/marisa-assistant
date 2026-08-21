"""Testes do tratamento de erro do webhook Telegram."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

import main
from agent import core


@pytest.mark.asyncio
async def test_handle_update_logs_and_sends_generic_error(
    monkeypatch: Any, caplog: Any
) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "123")
    monkeypatch.setattr(
        main, "get_settings", Mock(return_value=SimpleNamespace(telegram_admin_id=123))
    )
    process_message = Mock(side_effect=RuntimeError("unexpected failure"))
    send_message = AsyncMock()
    monkeypatch.setattr(main, "process_message", process_message)
    monkeypatch.setattr(main, "send_telegram_message", send_message)

    with caplog.at_level("ERROR"):
        await main.handle_update(
            {"message": {"from": {"id": 123}, "text": "teste"}}
        )

    process_message.assert_called_once_with(123, "teste")
    send_message.assert_called_once_with(123, main.ERROR_MESSAGE_GENERIC)
    assert "Falha ao processar update do Telegram" in caplog.text


def test_process_message_uses_history_and_returns_gemini_text(monkeypatch: Any) -> None:
    class FakeModels:
        def __init__(self) -> None:
            self.arguments: dict[str, Any] = {}

        def generate_content(self, **kwargs: Any) -> Any:
            self.arguments = kwargs
            return SimpleNamespace(text="resposta final", candidates=[])

    fake_models = FakeModels()
    fake_client = SimpleNamespace(models=fake_models)
    appended: list[tuple[int, str, str]] = []
    monkeypatch.setattr(core, "get_settings", Mock(gemini_model="modelo"))
    monkeypatch.setattr(core, "_get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(
        core,
        "load_recent_history",
        lambda chat_id: [{"role": "user", "content": "anterior"}],
    )
    monkeypatch.setattr(
        core,
        "append_message",
        lambda chat_id, role, content: appended.append((chat_id, role, content)),
    )

    result = core.process_message(123, "atual")

    assert result == "resposta final"
    assert len(fake_models.arguments["contents"]) == 2
    assert appended == [(123, "user", "atual"), (123, "model", "resposta final")]
