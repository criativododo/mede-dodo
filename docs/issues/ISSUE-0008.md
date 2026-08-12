# ISSUE-0008: Ancoragem na Realidade Física — Reparo do Pipeline de Dados Reais

## Objetivo
Diagnosticar e corrigir a causa raiz por trás de dados incoerentes ao rodar o pipeline
fora do Modo Demonstração (gênero indeterminado/incoerente, TER não refletindo a janela
selecionada, ausência de sinal demográfico real) — garantindo que o pipeline se comporte
de forma fiel a dados reais coletados do Instagram, não só em Modo Demonstração.

## Diagnóstico (investigação sistemática — Fase 1)
O relato inicial supunha um bug de "higienização de nomes" (handles como `@ana_silva` não
sendo limpos antes da consulta à base do IBGE). A investigação por rastreamento de código
(`grep -rn "get_comments\|date_utc" src/ app.py` → zero ocorrências antes deste reparo)
revelou uma causa raiz mais fundamental: **`instaloader_fetch_fn` (`src/scraper.py`) nunca
buscava comentários reais do Instagram** — só capturava `post.likes` e `post.comments`
(a contagem agregada, um inteiro), nunca chamava `post.get_comments()`. Isso significa que,
para qualquer perfil real, `all_comments_flat` em `app.py._run_pipeline` era sempre uma
lista vazia — não porque a inferência de gênero estivesse "invertida", mas porque não havia
nenhum dado de comentário para inferir nada (o resultado observável seria "indeterminado"
em 100% dos casos, não uma inversão sistemática F/M).

Uma segunda causa raiz, relacionada mas distinta, também foi confirmada: `instaloader_fetch_fn`
nunca capturava a data real de publicação de cada post (`post.date_utc`), e o corte por
`window_days` em `database.get_cached_data` filtra por `collected_at` (quando o post foi
raspado/cacheado), não por quando foi publicado no Instagram. Combinado com um teto fixo de
`MAX_POSTS_PER_FETCH = 12` (ignorando `window_days` por completo), o seletor de janela
30/60/90 dias na UI não correspondia aos posts realmente publicados nesse período — a TER
refletia "os últimos ≤12 posts raspados, seja qual for a idade deles", não "os posts
publicados na janela selecionada" como o RF-02 pretende.

## Tarefas de Implementação
1. **Comentários reais (`src/scraper.py`):**
   - `instaloader_fetch_fn` agora itera `post.get_comments()` para cada post dentro da
     janela, extraindo `{"username", "texto", "respondido"}` por comentário.
   - `respondido` é derivado checando se algum `comment.answers` tem `owner.username`
     igual ao `profile.username` (resposta real da criadora, RF-08).
2. **Janela real de publicação (`src/scraper.py`):**
   - Cada post coletado agora carrega `raw["published_at"]` (ISO 8601, UTC) a partir de
     `post.date_utc`.
   - A paginação de `profile.get_posts()` para no primeiro post mais antigo que
     `MAX_WINDOW_DAYS = 90` dias (a maior janela selecionável na UI), ou ao atingir
     `MAX_POSTS_SAFETY_CAP = 60` posts — o que vier primeiro. Isso substitui o corte fixo
     e arbitrário de 12 posts.
3. **Extração de nome a partir de handle (`src/demographics.py`):**
   - `extract_first_name_from_handle(handle)` deriva um candidato a primeiro nome de um
     `@handle`/username via regex (primeiro segmento alfabético — ex.: `"ana_silva92"` ->
     `"ana"`, `"_maria2000"` -> `"maria"`), sem nenhuma chamada de rede extra (evita o custo
     de resolver `full_name` via Profile de cada comentarista, que geraria uma requisição
     por comentarista único e violaria o throttling/custo-zero de `DUMMY.md`).
4. **Wiring em `app.py`:**
   - `_filter_posts_in_window(posts, window_days)` filtra os posts pela data real de
     publicação (`raw.published_at`) antes de qualquer cálculo de métrica — posts sem essa
     informação (Modo Demonstração, ou cache legado anterior a este reparo) não são
     descartados, mantendo compatibilidade retroativa.
   - A derivação de `nome` por comentário agora usa `c.get("nome") or
     demographics.extract_first_name_from_handle(c.get("username")) or "desconhecido"` —
     preserva o Modo Demonstração (que já injeta `"nome"` explícito) e resolve o modo real
     (que só tem `"username"`).
5. **Validação E2E (`tests/test_app.py`):**
   - Teste que simula a API do Instaloader (Profile/Post/Comment fake, sem rede) e roda
     `app._run_pipeline` fim-a-fim em modo real, provando que: um post fora da janela de 90
     dias não conta nas métricas; o gênero predominante é inferido corretamente a partir dos
     handles reais; a TER é calculada só sobre o post dentro da janela; e a publi na legenda
     do post recente é detectada (RF-09, ISSUE-0007).

## Critérios de Aceite (Definition of Done)
- [x] `instaloader_fetch_fn` popula `raw["comments"]` com dados reais de comentário
      (`username`, `texto`, `respondido`) para cada post dentro da janela.
- [x] `raw["published_at"]` capturado por post; janela de 90 dias e teto de segurança de 60
      posts substituem o corte fixo anterior.
- [x] `extract_first_name_from_handle` extrai um candidato a primeiro nome de um handle sem
      chamada de rede adicional.
- [x] `app.py` filtra posts pela data real de publicação antes de calcular métricas, e deriva
      `nome` do handle quando não há `"nome"` explícito no comentário.
- [x] Teste E2E simulando a API real do Instaloader passa fim-a-fim (comentários, janela,
      gênero, TER, publis).
- [x] Suíte completa: 96/96 testes passando (`pytest tests/`).

## Notas de Implementação
- **`extract_first_name_from_handle` é uma heurística, não uma extração garantidamente
  correta.** Handles que não seguem o padrão `nome_sobrenome`/`nome.numero` (ex.:
  `"melhorlojademoda"`, um handle de loja/marca comentando, não de pessoa) vão gerar um
  "nome" que não corresponde a nenhuma pessoa real — nesses casos `infer_gender` já
  retorna `"indeterminado"` corretamente (a base do IBGE não tem esse token como nome),
  então o pior caso é "sem sinal", nunca uma classificação errada com falsa confiança.
- **Por que não usar `comment.owner.full_name` (display name) em vez do handle?** O pedido
  original já apontava para extração via handle, e essa é também a escolha tecnicamente
  mais barata: resolver `full_name` via Instaloader exige buscar o objeto `Profile` completo
  de cada comentarista único, gerando uma requisição de rede adicional por autor — em um
  post com centenas de comentários isso explode o número de chamadas e viola a regra de
  throttling/custo-zero de `DUMMY.md`. A extração por handle é 100% local sobre dado já
  coletado.
- **`MAX_WINDOW_DAYS = 90` é a maior janela selecionável em `app.py` (`WINDOW_OPTIONS = [30,
  60, 90]`), não um valor livre.** Se a UI algum dia ganhar uma janela maior, essa constante
  precisa acompanhar — não há teste de sincronização automática entre os dois hoje, fica
  como débito técnico conhecido.
- **`MAX_POSTS_SAFETY_CAP = 60` é uma proteção de custo/rate-limit, não uma escolha de
  produto.** Perfis extremamente ativos (mais de 60 posts em 90 dias) terão a TER calculada
  sobre uma amostra truncada dos posts mais recentes dentro da janela, não sobre 100% deles
  — trade-off deliberado para não estourar a cota/throttling do Instagram em uma única
  coleta.
- **Validação com Instagram real ainda pendente.** Assim como registrado em ISSUE-0001, este
  reparo foi validado inteiramente com a API do Instaloader simulada (sem rede) — a
  verificação contra uma conta e sessão reais do Instagram continua sem ambiente disponível
  para teste nesta sessão.
