# Marisa Assistant

Assistente pessoal de produtividade acadêmica e gestão financeira, com
Telegram como canal, Gemini para orquestração, CalDAV para calendário e
Supabase para persistência.

## Desenvolvimento

1. Copie `.env.example` para `.env` e preencha as credenciais.
2. Aplique `database.sql` no projeto Supabase.
3. Instale as dependências com `uv sync`.
4. Execute os testes com `uv run pytest`.
5. Valide o código com `uv run mypy . --strict` e `uv run ruff check .`.

## Execução

```text
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Configure o webhook do Telegram para apontar para `/webhook` e use `/health`
para verificar se o serviço está respondendo.

As regras de comportamento, o contrato técnico, as decisões arquiteturais e
os procedimentos operacionais estão documentados em `AGENTS.md` e `docs/`.
