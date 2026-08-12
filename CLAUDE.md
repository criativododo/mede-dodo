# CLAUDE.md — Memória operacional (`metricaDODO`)

> Governa apenas como as sessões deste projeto iniciam, terminam e sincronizam contexto via o kit `.claude/session-memory/` (ADR-030, repositório `site`).

## Pendência bloqueante

Este projeto ainda não é um repositório Git formal. O kit exige um repositório Git na raiz (`ensureGitRepository`) para rodar `/inicio`/`/fim` — hoje o comando falha com `ERRO: Repositório da aplicação não é um repositório Git`. Antes de usar `/inicio` pela primeira vez, rode `git init` (e um primeiro commit) nesta pasta. Essa decisão fica para quem conduz o projeto — não foi tomada automaticamente durante a instalação do kit.

## Identidade

`projectId`: **`metricaDODO`** — inferido automaticamente pelo kit (remote Git → topo do worktree → `package.json` → nome da pasta; hoje resolve pelo nome da pasta, já que não há Git nem `package.json`/`pyproject.toml` com nome declarado). Nunca hardcodar esse valor em scripts.

## Memória operacional

- Hub compartilhado: `~/criativododo-memory` → `projects/metricaDODO/`.
- `executive-summary.md`, `journals/` (janela ativa) e `archive/YYYY-MM.md` são gerados pelo kit — não editar manualmente.

## Comandos

- `/inicio` — reconstrói o contexto da sessão a partir da memória Git antes de qualquer trabalho. Obrigatório no início de toda sessão (após resolver a pendência acima).
- `/fim` — encerra a sessão: gera journal factual, atualiza documentos derivados, valida, commita e publica no hub.
- `/status`, `/journal`, `/roadmap`, `/check` — consultas pontuais, sem alterar estado. `/check` roda `.venv/bin/python -m pytest tests/` (escopo `app`, ver `.claude/session-memory/config.json`).

## Isolamento

- Este projeto resolve seu próprio `projectId` e nunca compartilha pasta de memória com outro subprojeto de `~/0. PROJETO/`.
- `/fim` opera em worktree temporário próprio do repositório de memória e o remove ao concluir. Nunca editar `~/criativododo-memory` manualmente para contornar uma falha de validação — corrigir a causa e repetir `/fim`.

## Sincronização com o Google Drive

Desativada por padrão. Só é considerada quando existe um bloco declarativo `google_drive_sync` válido neste arquivo — sem ele, `driveSync.active` é sempre `false` (ver `lib/drive.mjs`). Estrutura de referência (ainda inativa — ative preenchendo o caminho real da pasta no Drive e trocando a cerca abaixo de ` ```text ` para ` ```google_drive_sync `):

```text
google_drive_sync
path: /caminho/absoluto/para/a/pasta/no/Drive
```
