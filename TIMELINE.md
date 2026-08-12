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

## 2026-08-12 (sprint de integração dos conectores reais)
- Execução em paralelo (2 subagentes concorrentes) de:
  - **ISSUE-0002/bugfix**: correção do falso positivo de região "para" (preposição) → PA
    (Pará) em `src/demographics.py`: `infer_region` só casa "PA" por menção quando a palavra
    aparece acentuada ("pará") no texto original, não na forma normalizada sem acento.
  - **ISSUE-0001**: `instaloader_fetch_fn` real (`src/scraper.py`, lib `instaloader`, sessão
    local por arquivo de cookies) e novo fallback gracioso de `scrape_profile` (tenta cache
    salvo sem filtro de janela antes de levantar `ScraperUnavailableError`).
  - **ISSUE-0003**: `RealGeminiClient` real (`src/gemini_analyzer.py`, SDK
    `google.generativeai`, JSON estruturado via `response_mime_type`, conversão de
    `ResourceExhausted` em `GeminiRateLimitError`); `requirements.txt` atualizado.
  - Suíte de testes: 61 → 70 (cumulativo), sempre verde.
- Integração dos dois conectores no pipeline de `app.py`: `RealGeminiClient()` instanciado
  quando o Modo Demonstração está desligado e `GEMINI_API_KEY` está definida (com
  tratamento gracioso de `RuntimeError` quando a chave falta); `scraper.instaloader_fetch_fn`
  usado como `fetch_fn` real fora do Modo Demonstração, com `cookies` lido da variável de
  ambiente `INSTAGRAM_SESSION_FILE`; novo status de UI `erro_coleta_indisponivel` para
  `scraper.ScraperUnavailableError`, exibido via `st.error` sem quebrar o app.
- Encontrado e corrigido, via TDD, um bug real em `src/exporter.py`: `generate_pdf_report`
  lançava `FPDFException: Not enough horizontal space to render a single character` ao
  renderizar 2 ou mais itens do Gemini (ou de publis), porque os `multi_cell` dentro desses
  loops não passavam `new_x`/`new_y` explícitos como o resto do arquivo — o cursor ficava
  perto da margem direita e a próxima célula de largura automática não cabia. Corrigido
  adicionando `new_x="LMARGIN", new_y="NEXT"` nos dois loops.
- Suíte de testes: 70 → 74 (2 testes novos de integração em `tests/test_app.py`, 2 testes de
  regressão do bug de PDF em `tests/test_exporter.py`), sempre verde.
- Documentação (`SPEC-001.md`, `DUMMY.md`, `PROGRESS.md`, `docs/issues/manifest.json`)
  atualizada para refletir a integração real concluída, mantendo como pendência explícita a
  validação com credenciais reais (Instagram e Gemini), indisponíveis neste ambiente.

## 2026-08-12 (RF-09 — Varredura de Publis, ISSUE-0007)
- `detect_sponsored_posts` (`src/filters.py`) implementado via TDD: regex local sobre
  legendas coletadas (`#publi`, `#ad`, `parceria`, `patrocinado`, menção `@marca`).
  Integrado ao pipeline de `app.py` (substitui a lista fixa `publis: []`); `demo_fetch_fn`
  ganhou legendas de exemplo para validar o fluxo fim-a-fim sem rede. UI e exportador
  (`src/exporter.py`) deixaram de exibir texto de "não implementado".
- Mensagem de falha de coleta real alinhada ao texto exato exigido; `genero_pct` exposto
  na demografia como prova quantitativa de que o engine já usa a base real do IBGE.
- Suíte de testes: 74 → 84.

## 2026-08-12 (Ancoragem na Realidade Física — reparo do pipeline de dados reais, ISSUE-0008)
- Investigação sistemática (Fase 1: root cause) encontrou uma causa raiz diferente da
  hipótese inicial (higienização de nome): `instaloader_fetch_fn` nunca chamava
  `post.get_comments()` — só capturava metadados agregados de post, deixando demografia/
  pods/Gemini sem nenhum comentário real para processar em qualquer perfil fora do Modo
  Demonstração. Segunda causa raiz relacionada: nenhuma data real de publicação era
  capturada, então o seletor de janela (30/60/90 dias) não correspondia aos posts
  realmente publicados nesse período para dados reais.
- Corrigido via TDD: `instaloader_fetch_fn` (`src/scraper.py`) agora busca comentários reais
  (`username`/`texto`/`respondido`) e a data real de publicação de cada post, respeitando
  `MAX_WINDOW_DAYS=90` e `MAX_POSTS_SAFETY_CAP=60`. `extract_first_name_from_handle`
  (`src/demographics.py`) deriva um candidato a primeiro nome de um `@handle` sem chamada de
  rede extra. `app.py` passou a filtrar posts pela data real de publicação e a usar o handle
  como fallback de nome quando não há `"nome"` explícito no comentário.
- Validado com teste E2E simulando a API do Instaloader fim-a-fim (comentários, janela,
  gênero, TER, publis), sem mocks de camadas intermediárias.
- Suíte de testes: 84 → 96.
