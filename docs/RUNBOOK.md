# RUNBOOK — Operação do Marisa Assistant

Guia rápido para manutenção recorrente e resposta a falhas. Referências: `AGENTS.md` (comportamento), `docs/TECHNICAL_SPEC.md` (contratos de código), `docs/adr/002-hardening-and-error-handling.md` (justificativa).

## 1. Início de cada semestre (obrigatório)

- [ ] Atualizar a tabela de grade horária em `AGENTS.md` Seção 2.1
- [ ] Atualizar o intervalo de validade em `AGENTS.md` Seção 2.2
- [ ] Rodar `tests/test_schedule_deduction.py` (contrato em `docs/TECHNICAL_SPEC.md` Seção 5) para confirmar que a dedução de dia/horário bate com a nova grade
- [ ] Fazer commit isolado (`chore: atualiza grade horária 2027/1`) para manter histórico auditável

## 2. Checklist antes de qualquer deploy

- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`
- [ ] Confirmar que `.env` não está no diff (`git status`)
- [ ] Verificar que `TELEGRAM_ADMIN_ID` no ambiente de produção corresponde ao seu ID real

## 3. O que fazer quando o bot "não responde"

1. Checar `/health` — se não responder, o serviço caiu (verificar logs da plataforma de deploy).
2. Se `/health` ok mas mensagens não chegam: verificar se o webhook do Telegram está registrado (`getWebhookInfo` da API do Telegram).
3. Checar logs por exceptions capturadas pelo `try/except` do `handle_update` (ADR 002, item 4) — toda falha deve aparecer logada com um `error_code` da tabela em `docs/TECHNICAL_SPEC.md` Seção 4, nunca silenciosa.
4. Se o log mostrar `CALDAV_UNAVAILABLE`: validar app-specific password da Apple (expira/é revogado com frequência).
5. Se o log mostrar `SUPABASE_UNAVAILABLE`: checar cota do free tier e status da instância.
6. Se o log mostrar `GEMINI_UNAVAILABLE`: checar status da API do Gemini e cota/rate limit da chave.

## 4. Rotação de segredos

- App-specific password da Apple: recriar a cada ~6 meses ou imediatamente se suspeitar de vazamento.
- `GEMINI_API_KEY` e `SUPABASE_KEY`: rotacionar se o repositório for tornado público em algum momento, mesmo que o `.gitignore` sempre tenha protegido o `.env`.

## 5. Sinais de que a memória de conversa precisa de limpeza

- Respostas da Marisa citando contexto de dias/semanas atrás incorretamente → truncar `conversation_history` mais agressivamente (reduzir de 10 para 5 mensagens) em `agent/core.py`.

## 6. Estado atual da integração com o iCloud

- O calendário CalDAV de eventos configurado para a aplicação é `Trabalho`.
- A lista de Lembretes `UFLA` aparece no iCloud, mas não é anunciada pela
  coleção CalDAV acessível pela conta usada no serviço.
- Enquanto a conta não expuser uma URL de tarefas compatível (`VTODO`), provas
  não devem ser redirecionadas para `Trabalho` nem criadas como eventos comuns.
- Se a Apple disponibilizar uma URL de tarefas para `UFLA`, atualizar
  `CALDAV_CALENDAR_URL` somente após confirmar a URL com uma operação de leitura
  e adicionar testes antes de alterar o comportamento de produção.
