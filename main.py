"""Webhook Telegram e tratamento de falhas do aplicativo."""

import logging
from typing import Any, Final

import httpx
from fastapi import BackgroundTasks, FastAPI

from agent.core import process_message
from config import get_settings

ERROR_MESSAGE_GENERIC: Final[str] = (
    "⚠️ Ocorreu um erro ao processar sua mensagem. Tente novamente."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)
app = FastAPI(title="Marisa Assistant")


def _extract_message(update_data: dict[str, Any]) -> tuple[int | None, str | None]:
    message = update_data.get("message")
    if not isinstance(message, dict):
        return None, None

    sender = message.get("from")
    if not isinstance(sender, dict) or not isinstance(sender.get("id"), int):
        return None, None

    text = message.get("text")
    if not isinstance(text, str):
        return sender["id"], None
    return sender["id"], text


async def send_telegram_message(chat_id: int, text: str) -> None:
    """Envia uma mensagem pela API do Telegram."""

    token = get_settings().telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json={"chat_id": chat_id, "text": text})
        response.raise_for_status()


async def handle_update(update_data: dict[str, Any]) -> None:
    """
    Processa um update autorizado e nunca propaga exceções ao chamador.

    Updates de usuários não autorizados e sem texto são descartados
    silenciosamente, conforme o contrato do webhook.
    """

    from_id, text = _extract_message(update_data)
    if from_id is None:
        return

    try:
        admin_id = get_settings().telegram_admin_id
    except Exception:
        logger.exception("Configuração inválida do administrador chat_id=%s", from_id)
        return

    if from_id != admin_id:
        return
    if text is None or not text.strip():
        return

    try:
        response_text = process_message(from_id, text)
        await send_telegram_message(from_id, response_text)
    except Exception:
        logger.exception(
            "Falha ao processar update do Telegram chat_id=%s",
            from_id,
        )
        try:
            await send_telegram_message(from_id, ERROR_MESSAGE_GENERIC)
        except Exception:
            logger.exception(
                "Falha ao enviar mensagem genérica do Telegram chat_id=%s",
                from_id,
            )


@app.get("/health")
async def health() -> dict[str, str]:
    """Endpoint de verificação operacional."""

    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    update_data: dict[str, Any], background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Aceita um update Telegram e agenda seu processamento."""

    background_tasks.add_task(handle_update, update_data)
    return {"status": "accepted"}
