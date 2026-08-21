# TECHNICAL_SPEC.md — Especificação de Implementação do Marisa Assistant

> Este é o documento normativo para qualquer agente ou desenvolvedor que for gerar código para este projeto. Onde houver conflito entre este arquivo e a intuição do implementador, **este arquivo vence**. Nenhuma função deve ser implementada com assinatura, tipo ou comportamento diferente do especificado aqui sem atualizar este documento primeiro.
>
> Documentos relacionados: `AGENTS.md` (comportamento do agente/persona), `docs/adr/002-hardening-and-error-handling.md` (justificativa das decisões), `docs/RUNBOOK.md` (operação).

---

## 1. Árvore de arquivos (definitiva)

```
marisa-assistant/
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── AGENTS.md
├── README.md
├── pyproject.toml
├── database.sql
├── config.py
├── main.py
├── agent/
│   ├── __init__.py
│   ├── core.py          # orquestração da chamada Gemini + histórico
│   ├── schemas.py        # FunctionDeclaration + Pydantic models de payload
│   ├── tools.py           # implementação real das 3 tools
│   ├── validation.py      # funções puras de validação/sanitização
│   ├── memory.py          # leitura/escrita de conversation_history
│   └── schedule.py        # dedução pura da grade horária vigente
├── docs/
│   ├── TECHNICAL_SPEC.md  # este arquivo
│   ├── RUNBOOK.md
│   └── adr/
│       ├── 001-stack-and-architecture.md
│       └── 002-hardening-and-error-handling.md
└── tests/
    ├── __init__.py
    ├── test_validation.py
    ├── test_schedule_deduction.py
    ├── test_tools.py
    └── test_webhook_error_handling.py
```

Nenhum arquivo fora dessa árvore deve ser criado sem justificativa registrada em um novo ADR.

---

## 2. Banco de dados

### 2.1 Tabela `transactions` (já existente, sem alteração de schema)

Ver `database.sql` original — mantém `id, amount, category, sub_category, description, created_at`.

### 2.2 Tabela `conversation_history` (nova — requerida pelo ADR 002 §2)

```sql
CREATE TABLE conversation_history (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    role VARCHAR(9) NOT NULL CHECK (role IN ('user', 'model')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_conversation_history_chat_id_created_at
    ON conversation_history (chat_id, created_at DESC);
```

**Regra de retenção:** a cada escrita, `agent/memory.py` deve podar registros além dos últimos `MAX_HISTORY_MESSAGES` (constante = 10) por `chat_id`. Poda é responsabilidade da aplicação, não do banco (sem trigger/cron — mantém a infra free-tier simples).

---

## 3. Contratos de módulo

Cada função abaixo é o contrato exato. Tipagem estrita (`mypy --strict` deve passar sem `# type: ignore`).

### 3.1 `agent/validation.py`

```python
def sanitize_text(value: str, *, max_length: int) -> str:
    """
    Remove caracteres de controle (exceto \n), colapsa espaços redundantes,
    escapa caracteres reservados de iCalendar (`\\`, `;`, `,`), e trunca
    para max_length. Levanta ValueError se, após sanitização, a string
    ficar vazia e max_length > 0.
    """

def validate_amount(value: float) -> float:
    """
    Levanta ValueError se value <= 0 ou value >= 100_000.
    Retorna o valor arredondado para 2 casas decimais.
    """

def validate_iso_datetime_range(start: str, end: str) -> tuple[datetime, datetime]:
    """
    Faz parse de start/end como ISO 8601 (timezone-aware,
    default America/Sao_Paulo se naive). Levanta ValueError se:
      - start ou end não são parseáveis
      - end <= start
      - start é anterior a 'agora - 1 hora' (tolerância para latência)
    Retorna a tupla (start_dt, end_dt).
    """

def validate_category(value: str) -> str:
    """
    Levanta ValueError se value não estiver em EXPENSE_CATEGORIES
    (constante definida em agent/schemas.py, espelhando o ENUM do banco).
    """
```

### 3.2 `agent/schemas.py`

```python
EXPENSE_CATEGORIES: Final[tuple[str, ...]] = (
    "Moradia", "Utilidades", "Alimentacao", "Transporte", "Assinaturas", "Compras",
)

class AddCalendarEventArgs(BaseModel):
    summary: str = Field(min_length=1, max_length=200)
    start_time: str
    end_time: str
    description: str = Field(default="", max_length=500)

class RecordExpenseArgs(BaseModel):
    amount: float
    category: Literal[EXPENSE_CATEGORIES]  # validado também via validate_category
    sub_category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=300)

class QueryExpensesArgs(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    category: str | None = None
    sub_category: str | None = None
```

`FunctionDeclaration` para o Gemini deve ser gerada a partir desses modelos Pydantic (via `model_json_schema()`), **não** por introspecção da assinatura da função Python de `tools.py`. Isso é o requisito central do ADR 002 §3 — a fonte de verdade do schema é o Pydantic model, não a função.

### 3.3 `agent/tools.py`

Cada tool segue o contrato:

```python
def add_calendar_event(args: AddCalendarEventArgs) -> ToolResult: ...
def record_expense(args: RecordExpenseArgs) -> ToolResult: ...
def query_expenses(args: QueryExpensesArgs) -> ToolResult: ...
```

```python
class ToolResult(BaseModel):
    ok: bool
    message: str          # texto curto, pt-BR, pronto para exibir ao usuário
    error_code: str | None = None   # ver Seção 4 (tabela de códigos)
```

Regras:
- Nenhuma tool deve deixar uma exceção de biblioteca externa (`caldav.error.*`, `httpx.*`, exceções do Supabase client) escapar. Toda chamada externa é envolvida em `try/except Exception` e traduzida para `ToolResult(ok=False, error_code=..., message=...)`.
- Validação (Seção 3.1) roda **antes** de qualquer chamada de rede. Erro de validação retorna `ToolResult` com `error_code="VALIDATION_ERROR"`, sem tocar em CalDAV/Supabase.

### 3.4 `agent/memory.py`

```python
def load_recent_history(chat_id: int, limit: int = 10) -> list[dict[str, str]]:
    """Retorna as últimas `limit` mensagens (role, content) em ordem cronológica ascendente."""

def append_message(chat_id: int, role: Literal["user", "model"], content: str) -> None:
    """Insere a mensagem e poda registros excedentes (Seção 2.2)."""
```

### 3.5 `agent/core.py`

```python
def process_message(chat_id: int, user_message: str) -> str:
    """
    1. sanitize_text(user_message, max_length=2000)
    2. history = load_recent_history(chat_id)
    3. monta `contents` = history + [mensagem atual]
    4. chama Gemini com tools declaradas via schemas.py
    5. se o modelo chamar uma tool: valida args com o Pydantic model
       correspondente ANTES de invocar agent/tools.py; erro de validação
       vira ToolResult(ok=False, error_code="VALIDATION_ERROR") devolvido
       ao próprio modelo como resultado da function call (não como
       exceção Python), permitindo que o Gemini corrija ou informe o usuário.
    6. append_message para ambos user e model.
    7. retorna response.text
    Nunca deixa exceção não tratada subir para main.py — qualquer falha
    aqui deve ser capturada e retornar uma string de erro genérica,
    delegando o log da exceção para o chamador via re-raise controlado
    (ver contrato de main.py, Seção 3.6).
    """
```

### 3.6 `main.py`

```python
async def handle_update(update_data: dict) -> None:
    """
    - Extrai from_id e text.
    - Se from_id != settings.TELEGRAM_ADMIN_ID: retorna silenciosamente (sem log, sem resposta).
    - Se text vazio/ausente: retorna silenciosamente.
    - Chama process_message dentro de try/except Exception:
        - except: logger.exception(...); envia ao usuário mensagem genérica
          de erro (constante ERROR_MESSAGE_GENERIC, ver Seção 4);
          NUNCA propaga a exceção (BackgroundTasks do FastAPI não expõe
          erros ao chamador, então engolir sem logar equivale a falha
          silenciosa total — o log é obrigatório).
    """
```

Logging: usar `logging` padrão da stdlib, configurado em `main.py` na inicialização (`logging.basicConfig(level=logging.INFO)`), formato incluindo timestamp e `chat_id` quando disponível. Nunca logar o conteúdo de `GEMINI_API_KEY`, `SUPABASE_KEY` ou `APP_SPECIFIC_PASSWORD`.

### 3.7 `agent/schedule.py`

```python
def deduce_class_time(
    event_date: date, discipline: str
) -> tuple[time, time] | None: ...
```

Retorna o horário da disciplina somente quando a data está dentro da validade
da grade e há uma correspondência inequívoca. Retorna `None` quando a data está
fora da validade, a disciplina não corresponde ao dia ou a dedução exige
confirmação do usuário.

---

## 4. Tabela de códigos de erro

| `error_code` | Quando ocorre | Mensagem padrão ao usuário |
|---|---|---|
| `VALIDATION_ERROR` | Payload de tool falha em validação (Seção 3.1) antes de qualquer chamada externa | "Não consegui entender algum dado — pode confirmar [campo]?" |
| `CALDAV_UNAVAILABLE` | Exceção ao conectar/gravar no CalDAV | "Não consegui acessar o calendário agora. Tente novamente em instantes." |
| `SUPABASE_UNAVAILABLE` | Exceção ao ler/gravar no Supabase | "Não consegui acessar o banco de dados agora. Tente novamente em instantes." |
| `GEMINI_UNAVAILABLE` | Exceção/timeout na chamada ao Gemini | (constante `ERROR_MESSAGE_GENERIC`: "⚠️ Ocorreu um erro ao processar sua mensagem. Tente novamente.") |
| `UNKNOWN` | Qualquer exceção não classificada | mesma constante `ERROR_MESSAGE_GENERIC` |

Todo `error_code` deve ser logado (`logger.exception` ou `logger.error`) com stack trace completo no servidor — a mensagem ao usuário é sempre a versão curta da tabela acima, nunca a stack trace ou o texto bruto da exceção.

---

## 5. Requisitos de teste (critério de aceite)

Um PR que altera `agent/` ou `main.py` só é aceito se:

- [ ] `tests/test_validation.py` cobre: valor negativo/zero/≥100000 em `validate_amount`; `end <= start` em `validate_iso_datetime_range`; categoria fora do enum; sanitização removendo caracteres de controle e truncando por `max_length`.
- [ ] `tests/test_schedule_deduction.py` cobre: data dentro da validade com disciplina única no dia (sucesso); data fora da validade (deve pedir confirmação, não inferir); disciplina em múltiplos dias sem correspondência exata (deve pedir confirmação).
- [ ] `tests/test_tools.py` cobre: cada tool com mock de cliente externo (CalDAV/Supabase) simulando exceção → confirma que retorna `ToolResult(ok=False, error_code=...)` em vez de propagar.
- [ ] `tests/test_webhook_error_handling.py` cobre: `handle_update` com `process_message` mockado para lançar exceção → confirma que uma mensagem de erro genérica é enviada ao Telegram e que a exceção é logada, não propagada.
- [ ] `uv run mypy .` passa em modo `strict` sem `# type: ignore` novos.
- [ ] `uv run ruff check .` sem warnings.

---

## 6. Fora de escopo (explícito)

Para evitar que um agente de código expanda o projeto além do combinado:

- Multi-tenant / múltiplos usuários — fora de escopo. `TELEGRAM_ADMIN_ID` único é intencional.
- Interface web — fora de escopo. Único canal é Telegram.
- Importação automática de grade horária (SIGAA ou similar) — fora de escopo nesta fase; atualização é manual via `docs/RUNBOOK.md` §1.
- Categorização automática de gastos via IA (ex.: inferir categoria a partir de texto livre sem o usuário informar) — fora de escopo; o usuário sempre informa a categoria explicitamente.
