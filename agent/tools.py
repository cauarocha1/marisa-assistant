"""Implementação das três tools externas do agente Marisa."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from caldav import DAVClient
from pydantic import BaseModel
from supabase import Client, create_client

from agent.schemas import (
    AddCalendarEventArgs,
    QueryExpensesArgs,
    RecordExpenseArgs,
)
from agent.validation import (
    sanitize_text,
    validate_amount,
    validate_category,
    validate_iso_datetime_range,
)
from config import get_settings

logger = logging.getLogger(__name__)

ERROR_MESSAGE_GENERIC = "⚠️ Ocorreu um erro ao processar sua mensagem. Tente novamente."
VALIDATION_ERROR_MESSAGE = "Não consegui entender algum dado — pode confirmar o campo informado?"
CALDAV_ERROR_MESSAGE = "Não consegui acessar o calendário agora. Tente novamente em instantes."
SUPABASE_ERROR_MESSAGE = "Não consegui acessar o banco de dados agora. Tente novamente em instantes."

_SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
_caldav_client_factory: Callable[..., Any] = cast(Callable[..., Any], DAVClient)
_supabase_client: Client | None = None


class ToolResult(BaseModel):
    """Resultado curto e seguro para exibição ou retorno ao Gemini."""

    ok: bool
    message: str
    error_code: str | None = None


def _validation_error(exc: ValueError) -> ToolResult:
    logger.error("tool validation failed error_code=VALIDATION_ERROR error=%s", exc)
    return ToolResult(
        ok=False,
        message=VALIDATION_ERROR_MESSAGE,
        error_code="VALIDATION_ERROR",
    )


def _get_supabase_client() -> Client:
    global _supabase_client

    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


def _get_query_date(value: str) -> str:
    sanitized = sanitize_text(value, max_length=50)
    try:
        parsed = datetime.fromisoformat(sanitized)
    except (TypeError, ValueError) as exc:
        raise ValueError("data de consulta inválida") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_SAO_PAULO_TZ)
    return parsed.isoformat()


def add_calendar_event(args: AddCalendarEventArgs) -> ToolResult:
    """Cria um evento no calendário CalDAV configurado."""

    try:
        summary = sanitize_text(args.summary, max_length=200)
        description = (
            sanitize_text(args.description, max_length=500) if args.description else ""
        )
        start_time, end_time = validate_iso_datetime_range(
            args.start_time, args.end_time
        )
    except ValueError as exc:
        return _validation_error(exc)

    try:
        settings = get_settings()
        client: Any = _caldav_client_factory(
            url=settings.caldav_url,
            username=settings.caldav_username,
            password=settings.app_specific_password,
        )
        calendar = client.calendar(url=settings.caldav_calendar_url)
        calendar.add_event(
            dtstart=start_time,
            dtend=end_time,
            summary=summary,
            description=description,
        )
    except Exception:
        logger.exception("tool failure error_code=CALDAV_UNAVAILABLE")
        return ToolResult(
            ok=False,
            message=CALDAV_ERROR_MESSAGE,
            error_code="CALDAV_UNAVAILABLE",
        )

    return ToolResult(ok=True, message="📅 Evento adicionado ao calendário.")


def record_expense(args: RecordExpenseArgs) -> ToolResult:
    """Registra uma despesa no Supabase configurado."""

    try:
        amount = validate_amount(args.amount)
        category = validate_category(args.category)
        sub_category = sanitize_text(args.sub_category, max_length=100)
        description = (
            sanitize_text(args.description, max_length=300) if args.description else ""
        )
    except ValueError as exc:
        return _validation_error(exc)

    try:
        _get_supabase_client().table("transactions").insert(
            {
                "amount": amount,
                "category": category,
                "sub_category": sub_category,
                "description": description,
            }
        ).execute()
    except Exception:
        logger.exception("tool failure error_code=SUPABASE_UNAVAILABLE")
        return ToolResult(
            ok=False,
            message=SUPABASE_ERROR_MESSAGE,
            error_code="SUPABASE_UNAVAILABLE",
        )

    return ToolResult(ok=True, message="💳 Gasto registrado.")


def query_expenses(args: QueryExpensesArgs) -> ToolResult:
    """Consulta despesas no Supabase com os filtros informados."""

    try:
        start_date = _get_query_date(args.start_date) if args.start_date else None
        end_date = _get_query_date(args.end_date) if args.end_date else None
        if start_date is not None and end_date is not None:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            if end_dt <= start_dt:
                raise ValueError("end_date deve ser posterior a start_date")
        category = validate_category(args.category) if args.category else None
        sub_category = (
            sanitize_text(args.sub_category, max_length=100)
            if args.sub_category
            else None
        )
    except ValueError as exc:
        return _validation_error(exc)

    try:
        query: Any = _get_supabase_client().table("transactions").select("*")
        if start_date is not None:
            query = query.gte("created_at", start_date)
        if end_date is not None:
            query = query.lte("created_at", end_date)
        if category is not None:
            query = query.eq("category", category)
        if sub_category is not None:
            query = query.eq("sub_category", sub_category)
        response = query.order("created_at", desc=True).execute()
        rows = cast(list[dict[str, Any]], response.data or [])
    except Exception:
        logger.exception("tool failure error_code=SUPABASE_UNAVAILABLE")
        return ToolResult(
            ok=False,
            message=SUPABASE_ERROR_MESSAGE,
            error_code="SUPABASE_UNAVAILABLE",
        )

    return ToolResult(ok=True, message=str(rows))
