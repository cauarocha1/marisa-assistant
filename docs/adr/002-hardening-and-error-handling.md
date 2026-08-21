# ADR 002: Hardening — Memória, Validação de Schema, Tratamento de Erro e Sanitização

## Status
Aceito

## Contexto

A versão inicial (ADR 001) validou a stack e a arquitetura serverless. Uma revisão crítica identificou 5 riscos que tornam o projeto inadequado para uso contínuo sem ajustes, mesmo sendo de uso pessoal:

1. Grade horária hardcoded sem validade — quebra silenciosamente a cada semestre.
2. Zero memória de conversa — cada mensagem é isolada, impedindo referências contextuais.
3. Function calling por introspecção automática de assinatura Python — frágil a mudanças de tipo/docstring.
4. Ausência de tratamento de erro no webhook — `BackgroundTasks` do FastAPI engole exceptions silenciosamente.
5. Ausência de sanitização de input antes de enviar dados ao CalDAV/Supabase.

## Decisões

### 1. Validade explícita da grade horária
A grade agora carrega um intervalo de validade (`2026-08-01` a `2026-12-19`) e uma regra de fallback: fora da validade, ou em caso de ambiguidade (disciplina em mais de um dia), o agente pergunta em vez de inferir. Ver `AGENTS.md` Seção 2.2.

**Trade-off:** a cada semestre é preciso atualizar manualmente o `AGENTS.md`. Aceito porque o volume de uso é baixo (1 usuário) e automatizar isso (ex.: importar do SIGAA) é escopo desproporcional ao ganho.

### 2. Memória de conversa de curto prazo
Adicionada tabela `conversation_history` no Supabase, guardando as últimas 10 mensagens (usuário + agente) por `chat_id`. `agent/core.py` monta o `contents` da chamada Gemini incluindo esse histórico, não apenas a mensagem atual.

**Trade-off:** aumenta o custo de tokens por chamada e adiciona uma tabela extra. Aceito porque sem isso o agente não consegue resolver referências temporais relativas ("segunda que vem"), que é um caso de uso central.

### 3. Schemas explícitos de tool (`FunctionDeclaration`)
Substituída a passagem direta de funções Python (`tools=[add_calendar_event, ...]`) por declarações explícitas em `agent/schemas.py`, com tipos, enums e limites de validação (ver AGENTS.md Seção 3). A validação de payload (tipo, range, enum) roda **antes** de a tool tocar em CalDAV/Supabase.

**Trade-off:** mais código boilerplate. Aceito porque elimina uma classe inteira de erro silencioso (mudança de assinatura Python quebrando o schema inferido sem aviso).

### 4. Tratamento de erro no webhook
`main.py` envolve `handle_update` em `try/except` explícito, loga a exceção (stdout estruturado, capturável pelo Render/Oracle) e envia uma mensagem de erro genérica ao usuário via Telegram, em vez de falhar silenciosamente dentro da `BackgroundTask`.

```python
async def handle_update(update_data: dict):
    try:
        ...
    except Exception as exc:
        logger.exception("Falha ao processar update do Telegram")
        await send_telegram_message(from_id, "⚠️ Ocorreu um erro ao processar sua mensagem. Tente novamente.")
```

**Trade-off:** nenhum — é estritamente uma correção de robustez, sem custo funcional.

### 5. Sanitização de input
Toda string recebida do usuário passa por uma função `sanitize_text()` (strip de caracteres de controle, limite de tamanho, escape de caracteres especiais de iCalendar/CalDAV como `\;,`) antes de ser usada em `add_calendar_event` ou `record_expense`.

**Trade-off:** pequeno overhead de processamento. Aceito por ser custo desprezível frente ao risco de payload malformado quebrar a integração CalDAV.

## Referência normativa

Os contratos exatos (assinaturas de função, modelos Pydantic, schema de banco, tabela de códigos de erro e critérios de aceite de teste) resultantes destas decisões estão especificados em `docs/TECHNICAL_SPEC.md`. Este ADR registra o *porquê*; o TECHNICAL_SPEC registra o *o quê exatamente implementar*.

## Consequências

- O agente fica mais lento por chamada (histórico + validação), mas isso é imperceptível em uso pessoal via Telegram.
- O código de `agent/tools.py` e `agent/core.py` cresce, mas ganha testabilidade — cada validação agora é uma função pura testável isoladamente (`tests/test_validation.py`).
- Fica registrado um processo operacional: atualizar `AGENTS.md` a cada início de semestre (ver `docs/RUNBOOK.md`).
