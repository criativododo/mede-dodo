# PROGRESS.md

## Status Atual
- [x] Infraestrutura física de pastas e arquivos criada.
- [x] SPEC-001 e DUMMY.md definidos.
- [x] **ISSUE-0001** — Coleta Local e Cache SQLite. `src/database.py`/`src/scraper.py`
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
  estava ausente de `requirements.txt` (drift de dependência) — adicionado. Ambos os bugs de
  sessão foram **validados com uma chamada real** (não mockada) nesta sessão: a sidebar
  mostrou corretamente "Sessão ativa: criativododo" e `instaloader_fetch_fn` de fato
  autenticou e enviou a requisição com a sessão correta. **Porém a validação real revelou
  que a hipótese original sobre a causa do Erro HTTP 400 estava incompleta**: lendo o código
  -fonte da lib instalada (`instaloader==4.15.3`), `Profile.from_username()` usa **sempre**
  o endpoint `api/v1/users/web_profile_info/`, autenticado ou não — não existe, nesta
  versão, uma rota GraphQL alternativa acionada por login. O 400 observado ao vivo para
  `@silviabraz` (`"Asset asset://laser.provider/ig_business_category_subvertical has been
  deleted. You cannot use this schema"`) é um **bug atual no backend do próprio Instagram**
  nesse endpoint, reproduzido de forma idêntica mesmo com sessão autenticada carregada
  corretamente — está fora do alcance de qualquer correção no lado do cliente (Instaloader
  não expõe, na versão pública mais recente, nenhum caminho alternativo em
  `Profile.from_username`). `@caroline_tanaka` passou pela etapa de perfil sem erro, mas
  falhou depois ao buscar comentários de um post via `i.instagram.com/api/v1/media/.../
  comments/` (`"something went wrong"` genérico — possivelmente transitório/rate-limit).
  Ver `docs/issues/ISSUE-0001.md` (seção "Validação real 2026-08-12") para o log completo e
  as opções de próximo passo. **Tratamento de erro resiliente adicionado em seguida**:
  `Profile.from_username()` e a busca de comentários (`_fetch_real_comments`) em
  `src/scraper.py` agora têm blocos `try/except` específicos (`ConnectionException` e
  `Exception`) que registram log do perfil/post afetado e seguem em frente — o bug de schema
  do Instagram vira um `ScraperUnavailableError` com mensagem clara (não sugere problema de
  sessão), e uma falha na busca de comentários de um post não aborta a coleta dos demais
  posts do perfil. Ver "Tratamento de erro resiliente" em `docs/issues/ISSUE-0001.md`.
  **Contorno implementado e validado ao vivo em seguida (2026-08-12)**: (1) corrigido o tipo
  real da exceção do bug de schema (`QueryReturnedBadRequestException`, que não é subclasse
  de `ConnectionException` — o `except` anterior nunca capturava o erro de verdade); (2)
  `_resolve_profile_via_topsearch` contorna o bug de schema resolvendo o perfil via
  `TopSearchResults` (endpoint diferente) quando logado; (3)
  `_fetch_comments_first_page_via_graphql` contorna a instabilidade do endpoint de
  comentários do app iPhone buscando a 1ª página via GraphQL direto; (4) corrigido bug
  adicional de posts fixados (pinned) antigos escondendo posts recentes reais no corte por
  janela de data. **Validado ao vivo contra o Instagram real** (por pedido explícito do
  usuário): `@silviabraz`, que antes falhava 100% com o bug de schema, agora resolve com
  sucesso via o fallback de topsearch (60 posts coletados); `@caroline_tanaka` confirmou que
  o endpoint de comentários do app iPhone falha de forma sistemática (100% dos posts
  amostrados, não pontual/rate-limit), mas o fallback via GraphQL recuperou comentários reais
  em todos os posts amostrados. ISSUE-0001 considerada **concluída** — ver "Contorno para o
  bug de schema e para comentários" e "Validação ao vivo do contorno" em
  `docs/issues/ISSUE-0001.md`.
- [x] **ISSUE-0002** — Filtragem Heurística e Demografia Local. `src/filters.py`
  (comentários rasos vs. alta intenção comercial) e `src/demographics.py` (gênero/região,
  interfaces injetáveis) prontos e testados. Bug do falso positivo "para" (preposição) → PA
  (Pará) corrigido.
- [~] **ISSUE-0003** — Processamento Gemini em Lote. `src/gemini_analyzer.py` (batching
  com teto de 2 chamadas/perfil, schema JSON, fallback gracioso de rate limit) pronto e
  testado com cliente mockado. **Migrado do SDK legado `google-generativeai` para o SDK
  oficial atual `google-genai`** (`requirements.txt`: `google-genai==2.17.0`;
  `RealGeminiClient` usa `from google import genai`/`self._client.models.generate_content`
  com `config=types.GenerateContentConfig(response_mime_type="application/json")` e
  `model="gemini-flash-latest"`; captura `google.genai.errors.APIError` para os códigos
  retryable 429/503, preservando o retry com backoff exponencial `[2, 4, 8]`s e o
  relançamento de `GeminiRateLimitError`; assinatura pública `generate_content(prompt) ->
  str` e `RealGeminiClient(model_name=...)` inalteradas para não quebrar `app.py`). Testes
  em `tests/test_gemini_analyzer.py` mockam a hierarquia real do SDK
  (`mock_client.models.generate_content`), sem depreciação. **Integrado ao pipeline de
  `app.py`** (instanciado quando `GEMINI_API_KEY` está no ambiente; ausência tratada graciosamente,
  sem quebrar o app). Pendente: chamada real à API do Gemini não testada neste ambiente
  (sem `GEMINI_API_KEY` disponível). Índice de pods deliberadamente fora do schema do
  Gemini (decisão de engenharia, ver ISSUE-0003.md). Prompt não oferece mais
  "desconhecida" como faixa etária padrão — o Gemini é instruído a sempre estimar.
  `summarize_brand_suitability` ganhou `distribuicao_intencao_compra` (proporção
  alta/média/baixa/nenhuma) e `faixa_etaria_predominante` (moda das faixas conhecidas),
  ambos exibidos em `app.py` (cards de taxa de comentários qualificados, distribuição de
  intenção de compra, sentimento e faixa etária predominante) — exportadores HTML/PDF
  (`src/exporter.py`) deliberadamente não tocados neste incremento (pedido explícito do
  usuário).
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
- [x] **Pacing/Anti-Ban (branch `worktree-pacing-anti-ban-progresso`, pendente de merge para
  `main`)** — `src/rate_controller.py` (`RateController`, novo): controlador de pacing
  conservador com `SafeStop` acionado em 429/403/challenge do Instagram, ligado de verdade
  ao pipeline real de `app.py` (não só instanciado — usado a cada requisição da coleta).
  `src/scraper.py` ganhou pacing por post (jitter entre posts, não só entre perfis) e
  propaga `SafeStop` sem cair no fallback de cache genérico quando a causa é bloqueio de
  segurança (evita mascarar um 429/checkpoint real como "sem dados"). `app.py` ganhou ETA
  dinâmico por média móvel (substitui estimativa fixa), mensagem de progresso contextual, o
  status novo `pausado_seguranca` (quando o `SafeStop` interrompe a coleta) e o botão "Ver
  Relatório" só libera a exportação HTML/PDF/JSON quando o pipeline chega de fato a
  `concluido`. Merge para `main` ainda não realizado — ver seção "Pendências" abaixo.

## Testes
**225/225 passando** (`.venv/bin/python -m pytest tests/`, validado nesta sessão a partir
do branch `worktree-pacing-anti-ban-progresso`), saída limpa quanto ao código do projeto —
resta 1 `DeprecationWarning` interno da própria lib `google-genai`
(`google/genai/types.py:42`, sobre `_UnionGenericAlias` do Python 3.14), não originado por
código deste repositório e fora do alcance de correção local. O SDK do Gemini **já foi
migrado de `google-generativeai` para `google-genai`** em sessão anterior (commit
`f7e08a9`, `requirements.txt: google-genai==2.17.0`, já presente em `main` antes deste
branch existir) — não fazia parte do trabalho pendente desta sessão.
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
sidebar em `tests/test_app.py`)
→ 135 (2026-08-12, tratamento de erro resiliente em `Profile.from_username()` e na busca de
comentários: +4 testes em `tests/test_scraper.py` reproduzindo o erro 400 de schema
removido e a interrupção parcial da busca de comentários).
→ 145 (2026-08-12, contorno para o bug de schema via `TopSearchResults` e para a
instabilidade de comentários via GraphQL direto: +10 testes em `tests/test_scraper.py`,
validado em seguida ao vivo contra `@silviabraz` e `@caroline_tanaka` reais).
→ 148 (2026-08-13, retry com backoff exponencial em `RealGeminiClient.generate_content`
para erros temporários 429/503 do Gemini, encontrado ao vivo no Streamlit: +3 testes em
`tests/test_gemini_analyzer.py`, ver ISSUE-0003.md).
→ 162 (2026-08-13, refinamento de qualidade das métricas/prompts do Gemini pedido pelo
usuário: filtro local reforçado contra elogio genérico decorado e comentários bot-like/spam
(`src/filters.py`), schema do prompt do Gemini enriquecido com `categoria_sentimento`/
`sinais_compra`, novo parecer local de aderência comercial (`summarize_brand_suitability`)
exibido em `app.py`/`src/exporter.py` sem alterar o layout Streamlit: +14 testes em
`tests/test_filters.py`, `tests/test_gemini_analyzer.py` e `tests/test_exporter.py`, ver
ISSUE-0003.md).
→ 168 (2026-08-13, agregados de audiência em nível de perfil: prompt do Gemini não oferece
mais "desconhecida" como faixa etária padrão, `summarize_brand_suitability` ganhou
`distribuicao_intencao_compra` e `faixa_etaria_predominante`, novos cards em `app.py`
(taxa de comentários qualificados, distribuição de intenção de compra, sentimento,
faixa etária predominante) — `src/exporter.py` deliberadamente intocado neste incremento;
+6 testes em `tests/test_gemini_analyzer.py` e `tests/test_app.py`. Criado também
`iniciar_app.command` na raiz, lançador de 1 clique para macOS que cria `.venv`, instala
dependências e sobe o Streamlit — testado ao vivo, subiu o servidor e respondeu HTTP 200).
→ (histórico de commits subsequentes em `main`, não detalhado passo a passo neste arquivo:
migração do SDK do Gemini para `google-genai`, retry 429/503, insights acionáveis de
campanha, PostScore canônico com duplo ranking — ver `git log main` e
`docs/issues/ISSUE-0003.md`) → 225 (2026-08-13, branch `worktree-pacing-anti-ban-progresso`:
+49 testes para `RateController`/pacing por post/`SafeStop`/ETA dinâmico/status
`pausado_seguranca`/botão Ver Relatório condicionado a `concluido`, ver bullet
"Pacing/Anti-Ban" acima).

## MVP: o que funciona hoje
Pipeline completo de ponta a ponta (`app.py`) em **Modo Demonstração** (dados fictícios
determinísticos, sem rede): input → filtragem → demografia → pods/score → relatório
HTML/PDF exportável. Validado com boot real via `AppTest` (não apenas testes unitários).
Fora do Modo Demonstração, o pipeline já usa os conectores reais
(`scraper.instaloader_fetch_fn` e `gemini_analyzer.RealGeminiClient`, este último só quando
`GEMINI_API_KEY` está definida). Desde a ISSUE-0008, `instaloader_fetch_fn` busca
comentários reais (não só metadados agregados de post) e filtra posts pela data real de
publicação dentro da janela selecionada (30/60/90 dias) — a integração de código está
completa e **validada ao vivo contra o Instagram real** (`@silviabraz` e `@caroline_tanaka`,
2026-08-12, ver ISSUE-0001.md), incluindo contornos funcionais para os dois bugs de backend
do Instagram encontrados no caminho. `RealGeminiClient` ainda não foi exercitado contra o
Gemini real neste ambiente.

## O que falta para sair de "demonstração" para uso real
1. Validar `RealGeminiClient` (`src/gemini_analyzer.py`) contra a API real do Gemini com
   uma `GEMINI_API_KEY` válida — a integração no pipeline de `app.py` já está completa e
   testada com mocks; falta a validação com chamada real — ISSUE-0003.
2. Validação da tabela de DDDs contra a fonte oficial ANATEL (indisponível nesta sessão)
   e, se desejado, ampliação da base de nomes além do top-1000/gênero.
3. Calibração dos pesos do Score DODÔ com dados reais de campanha (hoje é heurística).

## Pendências (2026-08-13)
1. ~~Merge do branch `worktree-pacing-anti-ban-progresso` para `main`~~ — **concluído**
   em sessão subsequente (2026-08-13): merge fast-forward em `main` (`8e25363`), 225/225
   testes validados no checkout principal, worktree removido com `git worktree remove`.
2. `RealGeminiClient` (SDK `google-genai`) segue sem validação contra a API real do Gemini
   neste ambiente (sem `GEMINI_API_KEY`) — mocks cobrem 100% do contrato, mas não uma
   chamada de rede real ao endpoint atual.

## Sprint 002 — Contrato canônico de métricas e proveniência (2026-08-13)
Primeira fase da Sprint 002 (`SPRINT-002/BENCHMARK-001.md` §6/§7, `SPRINT-002/ISSUE-001.md`
§5.3/§5.4/§6.2, `SPRINT-002/HANDOFF-SPRINT-002.md`), versionados nesta sessão junto com
`FINDER-0001.md`, `SPRINT-002/FINDER-001.md`, `SPRINT-002/FINDER-002.md` e
`SPRINT-002/FINDER-003.md` (eram documentação de planejamento pendente, só na raiz do
checkout principal, nunca commitada).

- **`src/metrics.py`** ganhou o contrato canônico de auditoria: `build_audit_report(posts,
  followers_count)` retorna `{"metrics": {...}, "provenance": [...]}`, com as 3 taxas de
  engajamento formais do benchmark (`calc_engagement_rate_by_followers`,
  `calc_engagement_rate_by_reach`, `calc_engagement_rate_by_views`). Cada métrica é um
  objeto autodescritivo — `value`, `unit`, `kind` (`derived`/`None` quando indisponível —
  ainda não há caso `observed`/`estimated`/`source_estimate` neste contrato inicial,
  restrito a taxas de engajamento derivadas), `source`, `confidence`, `denominator`,
  `included_actions`, `post_count`, `status` (`ok`/`indisponivel`) e `ressalvas` — em vez
  de um número solto, para nunca confundir "sem dado" com `0` silencioso (BENCHMARK-001.md
  §6: "o contrato também precisa distinguir `null` de zero").
  - `engagement_rate_by_followers`: média de `(likes + comments) / followers * 100` por
    post — mesma fórmula de `scoring.calc_engagement_rate`, porém como percentual e com
    proveniência; indisponível sem posts ou com `followers_count <= 0`.
  - `engagement_rate_by_reach`: `total_interactions / total_reach * 100`, somando só os
    posts da amostra com `estimated_reach` — a coleta local (Instaloader/scraping público)
    não fornece alcance hoje, então esta métrica fica `indisponivel` em qualquer auditoria
    real até existir uma fonte de alcance (Instagram Insights autenticado).
  - `engagement_rate_by_views`: `total_interactions / total_views * 100`, restrita a posts
    com `post_type` em `("reel", "reels")` e `views_count` presente — a coleta atual
    também não classifica `post_type`/`views_count`, então fica `indisponivel` até essa
    camada existir.
  - **Retrocompatibilidade preservada**: `scoring.calc_engagement_rate` (consumido por
    `app.py`/`src/exporter.py` como `analysis["engagement_rate"]`, um float simples) não
    foi tocado — o novo contrato é aditivo, ainda não plugado no pipeline/UI (isso é
    trabalho de uma fase seguinte da Sprint 002, fora do escopo desta entrega).
- **Testes**: +16 em `tests/test_metrics.py` cobrindo formato do contrato JSON
  (`json.dumps` sem exceção), as 3 fórmulas com valores conhecidos, preservação de
  `denominator`/`included_actions`/`post_count` e retorno `None`/`status="indisponivel"`
  para amostra vazia, seguidores zerados, ausência de `estimated_reach` e ausência de
  Reels com `views_count` — nunca lança exceção. Suíte completa: 225 → **241 testes,
  100% verde** (`.venv/bin/python -m pytest tests/`).
