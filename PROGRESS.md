# PROGRESS.md

## Status Atual
- [x] Infraestrutura física de pastas e arquivos criada.
- [x] SPEC-001 e DUMMY.md definidos.
- [~] **ISSUE-0001** — Coleta Local e Cache SQLite. `src/database.py`/`src/scraper.py`
  (cache, throttling, orquestração) prontos e testados. Pendente: `fetch_fn` real de
  raspagem do Instagram (sessão/cookies).
- [x] **ISSUE-0002** — Filtragem Heurística e Demografia Local. `src/filters.py`
  (comentários rasos vs. alta intenção comercial) e `src/demographics.py` (gênero/região,
  interfaces injetáveis) prontos e testados.
- [~] **ISSUE-0003** — Processamento Gemini em Lote. `src/gemini_analyzer.py` (batching
  com teto de 2 chamadas/perfil, schema JSON, fallback gracioso de rate limit) pronto e
  testado com cliente mockado. Pendente: cliente Gemini real. Índice de pods
  deliberadamente fora do schema do Gemini (decisão de engenharia, ver ISSUE-0003.md).
- [~] **ISSUE-0004** — Dashboard Streamlit e Exportador. `app.py` (pipeline em thread de
  background, Modo Demonstração, cards de Métricas/Demografia/Antifraude/Publis/Score) e
  `src/exporter.py` (HTML/PDF) prontos e testados, com boot real validado via `AppTest`.
  Pendente: dependem das pendências herdadas de ISSUE-0001/0003 para deixar de ser
  demonstração; RF-09 (publis) é placeholder explícito.
- [x] **ISSUE-0005** — Métricas de Antifraude (Pods) e Score DODÔ. `src/metrics.py`
  (`calc_pod_index`) e `src/scoring.py` (`calc_engagement_rate`, `calc_dodo_score`)
  prontos e testados. Pesos do score são heurística não calibrada com dados reais.
- [x] **ISSUE-0006** — Bases Locais de Demografia. `src/data_loaders.py` carrega 1.984
  nomes (base curada, derivada de dataset comunitário que cita a API do IBGE) e 67
  DDD→UF (fonte web, não validada contra a ANATEL oficial nesta sessão — site fora do ar).

## Testes
**61/61 passando** (`.venv/bin/python -m pytest tests/`), saída limpa, sem warnings.
Evolução: 28 (ISSUE-0001/2/3) → 43 (+ISSUE-0005) → 57 (+ISSUE-0006) → 61 (+ISSUE-0004).

## MVP: o que funciona hoje
Pipeline completo de ponta a ponta (`app.py`) em **Modo Demonstração** (dados fictícios
determinísticos, sem rede): input → filtragem → demografia → pods/score → relatório
HTML/PDF exportável. Validado com boot real via `AppTest` (não apenas testes unitários).

## O que falta para sair de "demonstração" para uso real
1. Raspagem real do Instagram (`fetch_fn` com cookies de sessão) — ISSUE-0001.
2. Cliente Gemini real (API key + SDK) — ISSUE-0003; `app.py` já aceita `gemini_client`
   real sem mudança de interface.
3. Varredura de publis (RF-09) — sem issue própria aberta ainda.
4. Validação da tabela de DDDs contra a fonte oficial ANATEL (indisponível nesta sessão)
   e, se desejado, ampliação da base de nomes além do top-1000/gênero.
5. Calibração dos pesos do Score DODÔ com dados reais de campanha (hoje é heurística).
6. Correção do falso-positivo de região ("para" → PA) em `src/demographics.py`, achado
   durante a integração da ISSUE-0004.
