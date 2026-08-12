# ISSUE-0004: Dashboard Streamlit e Exportador

## Objetivo
Entregar a interface Streamlit (`app.py`) que orquestra o pipeline completo (coleta/cache →
filtragem → demografia → pods/score → Gemini opcional → relatório) sem travar a UI, e o
exportador de relatório (`src/exporter.py`, HTML autocontido + PDF via fpdf2).

## Tarefas de Implementação
1. **`src/exporter.py`** — funções puras `generate_html_report(analysis)` e
   `generate_pdf_report(analysis)`, TDD estrito (RED confirmado com
   `tests/test_exporter.py` antes da implementação existir, depois GREEN).
2. **`app.py`** — input de perfil/URL (RF-01), seletor de janela 30/60/90 dias (RF-02),
   botão "Analisar" disparando o pipeline em `threading.Thread` de background, toggle
   "Modo demonstração", cards de Métricas/Demografia/Antifraude/Publis/Score DODÔ, botões
   de exportação HTML e PDF.
3. **`tests/test_app.py`** — smoke tests via `streamlit.testing.v1.AppTest` (RED confirmado
   antes de `app.py` existir: `FileNotFoundError`; depois GREEN).

## Critérios de Aceite (Definition of Done)
- [x] `generate_html_report`/`generate_pdf_report` implementados e testados (7/7 testes,
  TDD RED→GREEN confirmado).
- [x] `app.py` sobe sem exceção (`AppTest.from_file("app.py").run()`), com input de
  perfil/URL, seletor de janela e botão "Analisar" presentes (4/4 testes de smoke).
- [x] Coleta/raspagem roda em thread de background; a thread principal só faz
  polling/rerun (`st.progress` + `time.sleep(0.3)` + `st.rerun()`) — nunca bloqueia
  esperando a raspagem terminar (DUMMY.md #1). Validado com boot real via `AppTest`
  simulando clique em "Analisar" + modo demonstração até o pipeline concluir (ver Notas).
- [x] Quando `scraper.scrape_profile` lança `NotImplementedError` (sem `fetch_fn` real —
  ISSUE-0001), a UI mostra aviso claro referenciando a ISSUE-0001 e oferece o toggle
  "Modo demonstração".
- [x] "Modo demonstração" usa um `fetch_fn` local, determinístico (seed = username) e sem
  rede, rotulado explicitamente na UI como dado fictício.
- [x] Quando não há `client` Gemini configurado, a etapa é pulada com nota explícita na UI
  ("análise de intenção via Gemini não configurada nesta sessão") — não trava o pipeline.
- [x] Somente comentários já filtrados localmente (`filters.is_shallow_comment`) são
  elegíveis para o Gemini (DUMMY.md #2) — reforçado mesmo sem cliente real configurado.
- [x] `publis` é entregue como lista vazia (placeholder), rotulado explicitamente como
  RF-09 não implementado, tanto na UI quanto nos relatórios exportados.
- [x] Suíte completa do projeto: 61/61 testes via `pytest` (`tests/`), sem quebrar nada
  dos módulos de outras issues.

## Notas de Implementação

### Arquitetura de background thread (DUMMY.md #1)
`app.py::_run_pipeline(username, window_days, demo_mode, gemini_client, state)` roda em uma
`threading.Thread(daemon=True)` disparada pelo clique em "Analisar". Ela **nunca chama
widgets `st.*`** — só muta um dicionário Python puro (`state`), que é o próprio objeto
guardado em `st.session_state.pipeline_state` (mutação in-place, segura sob o GIL para
atribuição de chaves). A thread principal, a cada rerun, lê esse dicionário e decide o que
renderizar: se `status == "rodando"`, desenha a `st.progress` com a etapa atual, dorme 0.3s
e chama `st.rerun()` — nunca faz `thread.join()` nem espera de forma síncrona. Esse fluxo foi
validado de ponta a ponta simulando `AppTest`: preenchendo o input, ativando "Modo
demonstração" e clicando em "Analisar", o pipeline completo roda e popula
`st.session_state.pipeline_state["analysis"]` com o dicionário `analysis` no formato
canônico, sem exceções.

### Throttling em modo demonstração (DUMMY.md #3)
`scraper.scrape_profile` só chama `throttle_fn()` depois de confirmar que existe um
`fetch_fn` (ou seja, nunca antes de decidir se vai de fato "raspar"). Em modo real (sem
`fetch_fn`), a função levanta `NotImplementedError` antes de qualquer throttle — então o
`throttle_fn=scraper.throttle` (jitter real de 2-5s) só entraria em ação quando a raspagem
real (ISSUE-0001) existir de fato. Em **modo demonstração**, `app.py` passa
`throttle_fn=lambda: None` deliberadamente: o jitter de 2-5s existe para não sobrecarregar o
Instagram com requisições reais, e no modo demo não há nenhuma requisição de rede a proteger
— aplicar o jitter ali só atrasaria artificialmente a demonstração sem nenhum ganho de
segurança. Documentado aqui para deixar claro que essa é uma decisão consciente, não um
esquecimento da regra.

### Raspagem real ainda não implementada (herdado da ISSUE-0001)
Sem `fetch_fn` real, `scrape_profile` lança `NotImplementedError`. `app.py` captura essa
exceção dentro da thread de background, define `state["status"] = "erro_scraping_nao_implementado"`
e a UI mostra um aviso (`st.warning`) apontando para `docs/issues/ISSUE-0001.md` e sugerindo
ativar o "Modo demonstração". O modo demonstração (`demo_fetch_fn` em `app.py`) gera dados
100% fictícios e determinísticos (seed = `f"demo-{username}"`, via `random.Random`, sem
`time`/rede), incluindo um pequeno grupo de contas repetidoras propositalmente injetado em
metade dos posts para que o índice de pods (RF-08) tenha algo não-trivial para mostrar. A UI
rotula explicitamente o resultado como "MODO DEMONSTRAÇÃO" quando `state["demo_mode"]` é
verdadeiro — nunca disfarçado de dado real.

### Cliente Gemini real não integrado (herdado da ISSUE-0003)
`app.py` chama `_run_pipeline(..., gemini_client=None, ...)` — não há, nesta fase, nenhuma
forma de configurar uma chave de API real pela UI (fora de escopo desta issue). Quando
`gemini_client is None`, a etapa "gemini" do pipeline é pulada (`gemini_items = []`) e a UI
mostra a nota `exporter.GEMINI_NAO_CONFIGURADO_MSG` no card de comentários analisados e no
relatório exportado, em vez de travar ou fingir que a análise ocorreu. Mesmo quando um
`client` for injetado no futuro, apenas os comentários que passaram por
`filters.is_shallow_comment` (ou seja, o conjunto `qualified`) são enviados — nunca
comentários brutos (DUMMY.md #2).

### Publis (RF-09) — placeholder consciente
`analysis["publis"]` é sempre `[]` nesta issue — a varredura de publis (identificar posts
patrocinados) não foi escopo desta rodada. `src/exporter.py` e os cards de `app.py` mostram
explicitamente `exporter.PUBLIS_PLACEHOLDER_MSG` ("Varredura de publis (RF-09) não
implementada nesta rodada...") em vez de deixar a seção vazia sem explicação.

### Observação (não corrigida, fora do escopo desta issue): falso-positivo de região
Durante a validação de ponta a ponta em modo demonstração, um comentário fictício contendo a
palavra "para" (preposição comum, ex.: "prazo de entrega **para** SP") foi indevidamente
classificado como menção à região "PA" (Pará), porque
`src/demographics.DEFAULT_REGION_KEYWORDS` mapeia a palavra solta `"para"` → `"PA"`. Esse é
um problema pré-existente do dicionário parcial de `src/demographics.py` (já documentado como
"base parcial" na ISSUE-0002), não algo introduzido por esta issue — e `src/demographics.py`
está fora do escopo desta tarefa (instrução explícita de não tocar nesse arquivo). Registrando
aqui para não esconder o comportamento observado durante a integração real do pipeline.

### fpdf2 e caracteres fora de Latin-1
A fonte core `helvetica` do fpdf2 só suporta Latin-1. Textos do projeto usam travessão
tipográfico (`—`) em várias mensagens; `src/exporter.py::_pdf_safe` normaliza pontuação
tipográfica comum (travessão, aspas curvas, reticências) antes de qualquer `pdf.cell`/
`pdf.multi_cell`, evitando `FPDFUnicodeEncodingException` sem precisar embutir uma fonte
TrueType Unicode (o que aumentaria o tamanho do PDF gerado sem necessidade real para este
MVP).

### Ambiente e validação executada
- `.venv/bin/python -c "import ast; ast.parse(open('app.py').read())"` → sintaticamente
  válido.
- `.venv/bin/python -m pytest tests/test_exporter.py tests/test_app.py -v` → 11/11 GREEN.
- `.venv/bin/python -m pytest tests/ -v` → 61/61 GREEN (suíte completa do projeto, incluindo
  `metrics.py`/`scoring.py`/`data_loaders.py` dos outros 2 subagentes paralelos, que já
  existiam e passavam no momento desta integração).
- Boot real (não só sintático) validado via `AppTest`: preenchimento de `text_input`,
  ativação do `toggle` de modo demonstração e clique no botão "Analisar", com o pipeline de
  background rodando até `status == "concluido"` e populando `analysis` com todas as chaves
  do contrato canônico (`score_dodo`, `engagement_rate`, `demografia`, `antifraude`,
  `publis`, `comentarios_analisados`), mais o aparecimento dos dois botões de download
  (HTML e PDF).

## Pendências para integração futura
- Raspagem real do Instagram (`fetch_fn`, sessão/cookies) — ISSUE-0001, ainda em aberto.
- Cliente Gemini real (autenticação, chamada de rede) — ISSUE-0003, ainda em aberto; `app.py`
  já está pronto para receber um `client` real assim que existir (basta parametrizar
  `gemini_client` em vez de `None` fixo).
- Varredura de publis (RF-09) — issue própria futura, hoje só placeholder.
- Heurística de detecção de região por palavra-chave (`src/demographics.py`) tem
  falso-positivo conhecido com a palavra "para" — possível ajuste futuro (ex.: exigir
  capitalização ou contexto geográfico) em issue própria de melhoria da ISSUE-0002.
- Base oficial de nomes do IBGE e tabela completa de DDDs da ANATEL: `src/data_loaders.py`
  (subagente paralelo desta rodada) já entrega esses dados via `data/names_seed.json` e
  `data/ddd_uf.json`, consumidos por `app.py` normalmente.
