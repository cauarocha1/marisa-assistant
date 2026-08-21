"""Modelos de payload e declarações das tools da Marisa."""

from typing import Any, Final, Literal

from pydantic import BaseModel, Field

EXPENSE_CATEGORIES: Final[tuple[str, ...]] = (
    "Moradia",
    "Utilidades",
    "Alimentacao",
    "Transporte",
    "Assinaturas",
    "Compras",
)

ExpenseCategory = Literal[
    "Moradia",
    "Utilidades",
    "Alimentacao",
    "Transporte",
    "Assinaturas",
    "Compras",
]


class AddCalendarEventArgs(BaseModel):
    """Argumentos para criação de um evento no calendário."""

    summary: str = Field(min_length=1, max_length=200)
    start_time: str
    end_time: str
    description: str = Field(default="", max_length=500)


class RecordExpenseArgs(BaseModel):
    """Argumentos para registro de uma despesa."""

    amount: float
    category: ExpenseCategory
    sub_category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=300)


class QueryExpensesArgs(BaseModel):
    """Filtros para consulta de despesas."""

    start_date: str | None = None
    end_date: str | None = None
    category: str | None = None
    sub_category: str | None = None


def _function_declaration(
    name: str, description: str, model: type[BaseModel]
) -> dict[str, Any]:
    """Gera uma declaração Gemini a partir do schema Pydantic do payload."""

    return {
        "name": name,
        "description": description,
        "parameters": model.model_json_schema(),
    }


FUNCTION_DECLARATIONS: Final[tuple[dict[str, Any], ...]] = (
    _function_declaration(
        "add_calendar_event",
        "Agenda um evento no calendário do usuário.",
        AddCalendarEventArgs,
    ),
    _function_declaration(
        "record_expense",
        "Registra uma despesa informada pelo usuário.",
        RecordExpenseArgs,
    ),
    _function_declaration(
        "query_expenses",
        "Consulta despesas registradas no histórico financeiro.",
        QueryExpensesArgs,
    ),
)
