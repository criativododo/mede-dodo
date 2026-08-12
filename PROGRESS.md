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
  `erro_coleta_indisponivel` na UI). Reparado na ISSUE-0008: agora também busca comentários
  reais (`post.get_comments()`) e a data real de publicação de cada post — antes só
  coletava metadados agregados (likes/contagem de comentários), deixando demografia/pods/
  Gemini sem nenhum dado real para trabalhar. Reparado nesta sessão (2026-08-12): (1)
  `load_any_available_session(L)` autodetecta e carrega `~/.config/instaloader/session-*`
  automaticamente, sem depender de `INSTAGRAM_SESSION_FILE` — antes, sem essa variável, a
  coleta rodava 100% anônima mesmo havendo sessão salva; (2) corrigido bug real de
  identidade trocada — `load_session_from_file` era chamado com o username do perfil
  ANALISADO (ex. `silviabraz`) em vez do dono real dos cookies (ex. `criativododo`),
  extraído agora do próprio nome do arquivo de sessão; (3) sidebar do Streamlit mostra
  "Sessão ativa: `<usuario>`" ou avisa quando nenhuma sessão é detectada; (4) `instaloader`
  estava ausente de `requirements.txt` (drift de dependência) — adicionado. Essas duas
  causas explicam o Erro HTTP 400 relatado em perfis business/creator (requisição anônima
  cai no endpoint público instável `web_profile_info`; sessão autenticada usa GraphQL). Ver
  `docs/issues/ISSUE-0001.md` (seção "Reparo 2026-08-12") para o detalhamento completo,
  incluindo a pendência explícita de validação com uma chamada real ao Instagram (não
  disparada nesta sessão automatizada por prudência).
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
- [x] **ISSUE-0007** — Varredura de Publis (RF-09). `detect_sponsored_posts`
  (`src/filters.py`) varre legendas via regex (`#publi`, `#ad`, `parceria`, `patrocinado`,
  menção `@marca`) e está **integrado ao pipeline de `app.py`** (substitui a lista fixa
  `publis: []`). `demo_fetch_fn` ganhou legendas de exemplo (algumas patrocinadas) para
  validar o fluxo fim-a-fim sem rede. UI (`_render_publis_card`) e exportador
  (`src/exporter.py`) não exibem mais texto de "não implementado" — mostram a tabela real
  ou um estado vazio genuíno (`PUBLIS_VAZIO_MSG`). Também reparado nesta sessão: mensagem de
  falha de coleta real alinhada ao texto exato exigido (sem sugerir Modo Demonstração como
  alternativa a dados reais), e `genero_pct` exposto na demografia (prova quantitativa de
  que o engine já usa a base real do IBGE, não uma amostra sintética).

## Testes
**131/131 passando** (`.venv/bin/python -m pytest tests/`), saída limpa (1 warning de
depreciação do `google.generativeai`, fora do escopo desta sessão).
Evolução: 28 (ISSUE-0001/2/3) → 43 (+ISSUE-0005) → 57 (+ISSUE-0006) → 61 (+ISSUE-0004)
→ 70 (+fix região "para"/Pará, +`instaloader_fetch_fn` e fallback de cache)
→ 74 (+integração dos conectores reais no pipeline de `app.py`, +2 testes de `app.py`,
+2 testes de regressão do bug de PDF no exportador)
→ 84 (+ISSUE-0007: `detect_sponsored_posts` e sua integração ao pipeline/UI/exportador,
+prova de integração do engine demográfico com a base real do IBGE, +mensagem exata de
falha de coleta)
→ 96 (+ISSUE-0008: comentários reais e janela por data de publicação real em
`instaloader_fetch_fn`, +`extract_first_name_from_handle`, +filtro de janela e fallback de
nome em `app.py`, +teste E2E simulando a API do Instaloader fim-a-fim)
→ 122 (sessão de calibragem/reestruturação do pipeline de dados reais, ver commit
`d1912fd`/ISSUE-0008 no histórico do git — detalhamento não coberto neste arquivo)
→ 131 (2026-08-12, reparo dos gargalos de login/Erro HTTP 400: +7 testes de
`load_any_available_session`/`detect_available_session_username`/autodetecção de sessão em
`instaloader_fetch_fn` em `tests/test_scraper.py`, +2 testes de feedback de sessão na
sidebar em `tests/test_app.py`).

## MVP: o que funciona hoje
Pipeline completo de ponta a ponta (`app.py`) em **Modo Demonstração** (dados fictícios
determinísticos, sem rede): input → filtragem → demografia → pods/score → relatório
HTML/PDF exportável. Validado com boot real via `AppTest` (não apenas testes unitários).
Fora do Modo Demonstração, o pipeline já usa os conectores reais
(`scraper.instaloader_fetch_fn` e `gemini_analyzer.RealGeminiClient`, este último só quando
`GEMINI_API_KEY` está definida). Desde a ISSUE-0008, `instaloader_fetch_fn` busca
comentários reais (não só metadados agregados de post) e filtra posts pela data real de
publicação dentro da janela selecionada (30/60/90 dias) — a integração de código está
completa e validada com uma simulação fiel da API do Instaloader (teste E2E fim-a-fim),
mas ainda não foi exercitada contra o Instagram/Gemini reais neste ambiente.

## O que falta para sair de "demonstração" para uso real
1. Validar `instaloader_fetch_fn` (`src/scraper.py`) e a integração em `app.py` contra o
   Instagram real (sessão de cookies de verdade via `INSTAGRAM_SESSION_FILE`) — a
   interface, a integração no pipeline, a busca de comentários reais, o filtro de janela por
   data de publicação e o fallback de cache já estão implementados e testados com uma
   simulação fiel da API (Instaloader mockado); falta a validação com rede/conta reais —
   ISSUE-0001/ISSUE-0008.
2. Validar `RealGeminiClient` (`src/gemini_analyzer.py`) contra a API real do Gemini com
   uma `GEMINI_API_KEY` válida — a integração no pipeline de `app.py` já está completa e
   testada com mocks; falta a validação com chamada real — ISSUE-0003.
3. Validação da tabela de DDDs contra a fonte oficial ANATEL (indisponível nesta sessão)
   e, se desejado, ampliação da base de nomes além do top-1000/gênero.
4. Calibração dos pesos do Score DODÔ com dados reais de campanha (hoje é heurística).
