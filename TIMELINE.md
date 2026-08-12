# TIMELINE.md

## 2026-08-11
- Estrutura física do projeto criada (`specs/`, `decisions/`, `docs/issues/`, `legado/`).
- `SPEC-001.md`, `DUMMY.md`, `README.md`, `PROGRESS.md` definidos.

## 2026-08-12
- **ISSUE-0001** (parcial): `src/database.py` (cache SQLite) e `src/scraper.py`
  (throttling + orquestração) via TDD. Raspagem real do Instagram (`fetch_fn`) deixada
  como pendência explícita.
- **ISSUE-0002**: `src/filters.py` (comentários rasos vs. alta intenção comercial) e
  `src/demographics.py` (gênero por nome, região por DDD/menção) via TDD.
- **ISSUE-0003** (parcial): `src/gemini_analyzer.py` (batching com teto de 2
  chamadas/perfil, schema JSON, fallback gracioso de rate limit) via TDD, cliente Gemini
  real não integrado. Índice de repetição/pods deliberadamente removido do schema do
  Gemini (decisão de engenharia — ver Notas em ISSUE-0003.md).
- Execução em paralelo (3 subagentes concorrentes) de:
  - **ISSUE-0005**: `src/metrics.py` (`calc_pod_index`) e `src/scoring.py`
    (`calc_engagement_rate`, `calc_dodo_score`) via TDD.
  - **ISSUE-0006**: `src/data_loaders.py` — base de nomes (1.984 nomes, derivada do
    dataset comunitário `MedidaSP/nomes-brasileiros-ibge`) e tabela DDD→UF (67 códigos).
  - **ISSUE-0004**: `src/exporter.py` (relatório HTML/PDF) e `app.py` (dashboard
    Streamlit com pipeline em thread de background, Modo Demonstração).
- Suíte de testes: 28 → 43 → 57 → 61 testes, sempre verde, ao longo das rodadas acima.
- MVP funcional de ponta a ponta em Modo Demonstração (sem rede real).
