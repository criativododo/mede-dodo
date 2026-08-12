# PROGRESS.md

## Status Atual
- [x] Infraestrutura física de pastas e arquivos criada.
- [x] SPEC-001 e DUMMY.md definidos.
- [~] **ISSUE-0001** — Coleta Local e Cache SQLite. `src/database.py`/`src/scraper.py`
  (cache, throttling, orquestração) prontos e testados. `instaloader_fetch_fn` (via
  instaloader, sessão local por arquivo de cookies em `INSTAGRAM_SESSION_FILE`) implementado
  e **integrado ao pipeline de `app.py`** (usado como `fetch_fn` sempre que o Modo
  Demonstração está desligado), com fallback gracioso para cache SQLite
  (`ScraperUnavailableError` só quando não há cache algum, agora tratado como status próprio
  `erro_coleta_indisponivel` na UI). Pendente: validação com sessão/cookies reais do
  Instagram (não testável localmente sem rede/credenciais neste ambiente).
- [x] **ISSUE-0002** — Filtragem Heurística e Demografia Local. `src/filters.py`
  (comentários rasos vs. alta intenção comercial) e `src/demographics.py` (gênero/região,
  interfaces injetáveis) prontos e testados. Bug do falso positivo "para" (preposição) → PA
  (Pará) corrigido.
- [~] **ISSUE-0003** — Processamento Gemini em Lote. `src/gemini_analyzer.py` (batching
  com teto de 2 chamadas/perfil, schema JSON, fallback gracioso de rate limit) pronto e
  testado com cliente mockado. `RealGeminiClient` (SDK `google.generativeai` real,
  `GeminiRateLimitError` para cota) implementado e **integrado ao pipeline de `app.py`**
  (instanciado quando `GEMINI_API_KEY` está no ambiente; ausência tratada graciosamente,
  sem quebrar o app). Pendente: chamada real à API do Gemini não testada neste ambiente
  (sem `GEMINI_API_KEY` disponível). Índice de pods deliberadamente fora do schema do
  Gemini (decisão de engenharia, ver ISSUE-0003.md).
- [x] **ISSUE-0004** — Dashboard Streamlit e Exportador. `app.py` (pipeline em thread de
  background, Modo Demonstração, cards de Métricas/Demografia/Antifraude/Publis/Score,
  conectores reais de scraper e Gemini já plugados) e `src/exporter.py` (HTML/PDF) prontos
  e testados, com boot real validado via `AppTest`. Corrigido bug real no exportador de PDF
  (`FPDFException: Not enough horizontal space...` ao renderizar 2+ itens do Gemini ou de
  publis, por falta de `new_x`/`new_y` explícitos em `multi_cell` dentro de loops).
  Pendente: RF-09 (publis) segue placeholder explícito; validação fim-a-fim com dados reais
  (Instagram + Gemini) depende das credenciais pendentes em ISSUE-0001/0003.
- [x] **ISSUE-0005** — Métricas de Antifraude (Pods) e Score DODÔ. `src/metrics.py`
  (`calc_pod_index`) e `src/scoring.py` (`calc_engagement_rate`, `calc_dodo_score`)
  prontos e testados. Pesos do score são heurística não calibrada com dados reais.
- [x] **ISSUE-0006** — Bases Locais de Demografia. `src/data_loaders.py` carrega 1.984
  nomes (base curada, derivada de dataset comunitário que cita a API do IBGE) e 67
  DDD→UF (fonte web, não validada contra a ANATEL oficial nesta sessão — site fora do ar).

## Testes
**74/74 passando** (`.venv/bin/python -m pytest tests/`), saída limpa (1 warning de
depreciação do `google.generativeai`, fora do escopo desta sessão).
Evolução: 28 (ISSUE-0001/2/3) → 43 (+ISSUE-0005) → 57 (+ISSUE-0006) → 61 (+ISSUE-0004)
→ 70 (+fix região "para"/Pará, +`instaloader_fetch_fn` e fallback de cache)
→ 74 (+integração dos conectores reais no pipeline de `app.py`, +2 testes de `app.py`,
+2 testes de regressão do bug de PDF no exportador).

## MVP: o que funciona hoje
Pipeline completo de ponta a ponta (`app.py`) em **Modo Demonstração** (dados fictícios
determinísticos, sem rede): input → filtragem → demografia → pods/score → relatório
HTML/PDF exportável. Validado com boot real via `AppTest` (não apenas testes unitários).
Fora do Modo Demonstração, o pipeline já usa os conectores reais
(`scraper.instaloader_fetch_fn` e `gemini_analyzer.RealGeminiClient`, este último só quando
`GEMINI_API_KEY` está definida) — a integração de código está completa e testada com mocks,
mas ainda não foi exercitada contra o Instagram/Gemini reais neste ambiente.

## O que falta para sair de "demonstração" para uso real
1. Validar `instaloader_fetch_fn` (`src/scraper.py`) e a integração em `app.py` contra o
   Instagram real (sessão de cookies de verdade via `INSTAGRAM_SESSION_FILE`) — a
   interface, a integração no pipeline e o fallback de cache já estão implementados e
   testados com mocks; falta a validação com rede/conta reais — ISSUE-0001.
2. Validar `RealGeminiClient` (`src/gemini_analyzer.py`) contra a API real do Gemini com
   uma `GEMINI_API_KEY` válida — a integração no pipeline de `app.py` já está completa e
   testada com mocks; falta a validação com chamada real — ISSUE-0003.
3. Varredura de publis (RF-09) — sem issue própria aberta ainda.
4. Validação da tabela de DDDs contra a fonte oficial ANATEL (indisponível nesta sessão)
   e, se desejado, ampliação da base de nomes além do top-1000/gênero.
5. Calibração dos pesos do Score DODÔ com dados reais de campanha (hoje é heurística).
