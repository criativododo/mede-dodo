# CLAUDE.md — Memória operacional (`metricaDODO`)

## IDIOMA DE COMUNICAÇÃO (OBRIGATÓRIA)

Responda SEMPRE estritamente em Português do Brasil (PT-BR) em todas as respostas, relatórios, resumos e opções. É proibido responder em inglês.

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

## Sincronização seletiva com o Google Drive

A sincronização `/drive` é **unidirecional**: somente o checkout local envia arquivos para o espelho do Google Drive, que alimenta o contexto normativo do Gemini Spark. O comando não baixa alterações do Drive e não deve ser usado para sincronizar dados brutos, credenciais ou histórico legado.

```google_drive_sync
drive_url: https://drive.google.com/drive/folders/1ytT3dHcVfqnSeggYqPB-VINlndJHInV4?usp=drive_link
path: /Users/danielperrut/Library/CloudStorage/GoogleDrive-criativododo@gmail.com/Meu Drive/0. SISTEMA D/sub-projects/mede-dodo
direction: local_to_drive
mode: selective_whitelist
```

### Whitelist de sincronização

- `README.md`, `DUMMY.md`, `PROGRESS.md` e `FINDER-001.md` na raiz;
- todos os arquivos ativos em `specs/`;
- todos os arquivos em `decisions/`;
- todos os arquivos em `docs/issues/`;
- todos os arquivos `BENCHMARK-METRICS-*.md` na raiz.

### Blacklist obrigatória

Nunca sincronizar `/legado/`, `/data/`, `.env`, sessões do Instaloader, `.git/`, `__pycache__/`, `.pytest_cache/`, `venv/`, `.DS_Store` ou qualquer credencial, cache, segredo ou diretório de sistema. O próprio `CLAUDE.md` permanece local e não faz parte da whitelist.
