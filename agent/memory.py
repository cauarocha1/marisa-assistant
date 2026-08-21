"""Persistência da memória curta da conversa no Supabase."""

from typing import Any, Final, Literal, cast

from supabase import Client, create_client

from config import get_settings

MAX_HISTORY_MESSAGES: Final[int] = 10

_supabase_client: Client | None = None


def _get_supabase_client() -> Client:
    global _supabase_client

    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


def load_recent_history(chat_id: int, limit: int = 10) -> list[dict[str, str]]:
    """Retorna as últimas mensagens em ordem cronológica ascendente."""

    response = (
        _get_supabase_client()
        .table("conversation_history")
        .select("role, content")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    return [
        {"role": str(row["role"]), "content": str(row["content"])}
        for row in reversed(rows)
    ]


def append_message(chat_id: int, role: Literal["user", "model"], content: str) -> None:
    """Insere uma mensagem e poda o histórico excedente do chat."""

    client = _get_supabase_client()
    (
        client.table("conversation_history")
        .insert({"chat_id": chat_id, "role": role, "content": content})
        .execute()
    )

    response = (
        client.table("conversation_history")
        .select("id")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .range(MAX_HISTORY_MESSAGES, 100_000)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    ids_to_delete = [row["id"] for row in rows]
    if ids_to_delete:
        client.table("conversation_history").delete().in_("id", ids_to_delete).execute()
