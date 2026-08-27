# Marisa Assistant

Assistente pessoal da Marisa para organização acadêmica e controle financeiro.
O projeto recebe mensagens pelo Telegram, usa o Gemini para interpretar cada
pedido, grava dados no Supabase e cria eventos no calendário CalDAV configurado.

> Status atual: a integração com calendário está funcionando para eventos
> comuns. A lista de Lembretes `UFLA` aparece no iCloud, mas não está exposta
> pelo endpoint CalDAV disponibilizado pela conta; por isso, provas ainda não
> são redirecionadas nem simuladas como eventos. Essa limitação está registrada
> em [docs/RUNBOOK.md](docs/RUNBOOK.md).

## O que já está funcionando

- Recebimento e resposta de mensagens pelo Telegram.
- Restrição do webhook ao administrador configurado.
- Registro e consulta de despesas no Supabase.
- Registro de histórico recente das conversas.
- Criação de eventos no calendário CalDAV selecionado.
- Validação de valores, categorias, datas e campos obrigatórios.
- Tratamento seguro de falhas externas, sem expor credenciais ou detalhes
  internos ao usuário.
- Endpoint `/health` para verificar se a aplicação está respondendo.

## Como a aplicação funciona

```text
Telegram
   ↓
FastAPI (/webhook)
   ↓
Gemini + function calling
   ├── Supabase: despesas e histórico
   └── CalDAV: eventos do calendário configurado
   ↓
Resposta objetiva no Telegram
```

## Pré-requisitos

- Python 3.12.x.
- [uv](https://docs.astral.sh/uv/).
- Um bot criado no Telegram pelo `@BotFather`.
- ID numérico da conta autorizada a usar o bot.
- Chave da API Gemini.
- Projeto Supabase com o script `database.sql` aplicado.
- Conta Apple com senha específica de aplicativo para o CalDAV.

## Configuração local

1. Copie `.env.example` para `.env`.
2. Preencha as variáveis abaixo. O arquivo `.env` é local e não deve ser
   enviado ao GitHub.
3. Execute `database.sql` no SQL Editor do Supabase.
4. Instale as dependências:

   ```powershell
   uv sync --all-groups
   ```

### Variáveis de ambiente

| Variável | Finalidade |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token fornecido pelo `@BotFather`. |
| `TELEGRAM_ADMIN_ID` | ID numérico do usuário autorizado. |
| `GEMINI_API_KEY` | Chave da API do Gemini. |
| `GEMINI_MODEL` | Modelo usado pelo agente, por exemplo `gemini-3.6-flash`. |
| `SUPABASE_URL` | URL base do projeto Supabase, sem `/rest/v1/`. |
| `SUPABASE_KEY` | Chave de acesso usada pela aplicação. |
| `CALDAV_URL` | Endpoint CalDAV, normalmente `https://caldav.icloud.com/`. |
| `CALDAV_USERNAME` | Identificador da conta Apple usada no CalDAV. |
| `APP_SPECIFIC_PASSWORD` | Senha específica de aplicativo da Apple. |
| `CALDAV_CALENDAR_URL` | URL exata do calendário CalDAV que receberá os eventos. |

Para a conta atualmente configurada, o calendário de eventos usado é
`Trabalho`. A URL deve ser a do calendário, e não apenas a URL base do iCloud.

## Executar e validar

Inicie o servidor local:

```powershell
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Em outro terminal, execute a suíte e as verificações de qualidade:

```powershell
uv run pytest
uv run mypy . --strict
uv run ruff check .
```

Com o servidor em execução, o endpoint de saúde fica disponível em
`http://localhost:8000/health`.

## Exemplos de uso

As mensagens podem ser escritas em linguagem natural, por exemplo:

- `Oi, Marisa`
- `Gastei R$ 32,90 com alimentação no RU hoje`
- `Quanto gastei com transporte este mês?`
- `Crie um evento chamado Prova de Cálculo para 15/09 às 14h`

O ano não precisa ser informado quando o pedido se refere ao ano corrente.
Datas, valores e categorias são normalizados e validados antes de qualquer
gravação.

## Deploy no Render

Configuração utilizada pelo serviço:

- Runtime: `Python 3`.
- Versão: `3.12.13`.
- Build command: `uv sync --frozen --no-dev`.
- Start command: `uv run uvicorn main:app --host 0.0.0.0 --port $PORT`.

No Render, cadastre todas as variáveis do `.env` em **Environment**. Nunca
cole o conteúdo do `.env` em commits, issues, prints ou mensagens públicas.

Depois do deploy, valide:

```text
https://SEU-SERVICO.onrender.com/health
```

O webhook do Telegram deve apontar para:

```text
https://SEU-SERVICO.onrender.com/webhook
```

O endereço atualmente publicado é
[marisa-assistant.onrender.com](https://marisa-assistant.onrender.com).

## Calendário e lembretes UFLA

O iCloud apresenta calendários de eventos e listas de Lembretes como recursos
distintos. O serviço mantém, por enquanto, a criação de eventos no calendário
CalDAV configurado. A lista `UFLA` foi criada no iCloud, mas não foi descoberta
no conjunto de calendários CalDAV acessível pela conta usada pela aplicação.

Consequentemente, o comportamento atual é deliberado: a aplicação não cria
uma prova como evento comum fingindo que ela é um lembrete e não envia o item
para outro calendário. A implementação de provas como lembretes depende de uma
URL CalDAV de tarefas (`VTODO`) que a conta efetivamente exponha.

## Segurança

- `.env` e `.env.txt` estão no `.gitignore`.
- Nunca publique tokens do Telegram, chaves do Gemini, chaves do Supabase ou
  senhas específicas da Apple.
- Se uma credencial for exposta, revogue-a e gere outra imediatamente.
- O bot deve permanecer restrito ao `TELEGRAM_ADMIN_ID` configurado.

## Documentação do projeto

- [AGENTS.md](AGENTS.md): regras de desenvolvimento do repositório.
- [docs/TECHNICAL_SPEC.md](docs/TECHNICAL_SPEC.md): contrato técnico
  normativo.
- [docs/RUNBOOK.md](docs/RUNBOOK.md): operação, diagnóstico e deploy.
- [docs/adr/002-hardening-and-error-handling.md](docs/adr/002-hardening-and-error-handling.md):
  decisões de robustez e tratamento de erros.
- [database.sql](database.sql): estrutura necessária no Supabase.
