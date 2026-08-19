# ISSUE-0007: Varredura de Publis (RF-09)

## Objetivo
Mapear, a partir das legendas já coletadas pelo pipeline (`src/scraper.py`), postagens que
indicam parceria comercial (publi/patrocínio) — marca mencionada e link do post — sem
depender de nenhuma chamada externa (LLM ou rede): só regex local sobre texto já raspado,
seguindo o mesmo espírito 100% local das demais heurísticas do projeto (RF-05/RF-06).

## Tarefas de Implementação
1. **`detect_sponsored_posts(posts)` (`src/filters.py`):**
   - Recebe `posts: list[{"post_id": str, "raw": {"caption": str|None, "shortcode": str|None, ...}}]`
     — o mesmo formato de post usado em todo o pipeline (`app.py`/`src/scraper.py`).
   - Varre a legenda de cada post com os padrões: `#publi` (e variações, ex. `#publiparceria`),
     `#ad`, `parceria`, `patrocinado`/`patrocinada`, e menções de marca via `@handle`.
   - Retorna uma lista de itens `{"post_id", "shortcode", "link", "termos", "marcas"}`, onde
     `link` é `https://www.instagram.com/p/{shortcode}/` (ou `None` sem `shortcode`), `termos`
     lista quais padrões casaram (incluindo `"mencao_marca"` quando há `@handle`), e `marcas`
     lista os handles encontrados. Posts sem legenda ou sem nenhum indício são ignorados.
2. **Integração ao pipeline (`app.py`):**
   - `_run_pipeline` chama `filters.detect_sponsored_posts(posts)` logo após a filtragem de
     comentários rasos, e o resultado alimenta `analysis["publis"]` (antes sempre `[]`).
   - `demo_fetch_fn` passou a gerar `caption`/`shortcode` por post (1 a cada 3 posts com
     legenda patrocinada de exemplo), para que o Modo Demonstração continue validando o
     pipeline fim-a-fim sem rede — incluindo RF-09.
3. **UI e exportador sem placeholder:**
   - `app.py._render_publis_card` renderiza uma tabela real (link do post, indícios, marca)
     quando há publis detectadas, ou uma legenda de estado vazio genuíno quando não há.
   - `src/exporter.py`: `PUBLIS_PLACEHOLDER_MSG` ("não implementada") foi substituída por
     `PUBLIS_VAZIO_MSG` ("nenhuma publi identificada"); HTML e PDF agora formatam os itens
     reais (link clicável no HTML, texto com link/indícios/marca no PDF) em vez de tratar
     `publis` como uma lista genérica de strings.

## Critérios de Aceite (Definition of Done)
- [x] `detect_sponsored_posts` detecta `#publi`, `#ad`, `parceria`, `patrocinado` e menções
      `@marca`, e ignora posts sem legenda ou sem indício comercial.
- [x] Pipeline real (`_run_pipeline`) popula `analysis["publis"]` com os itens detectados —
      não é mais uma lista vazia fixa.
- [x] Modo Demonstração também exercita a detecção (legendas de exemplo, algumas
      patrocinadas), sem depender de rede.
- [x] UI (`app.py`) e exportador (`src/exporter.py`) não exibem mais texto de "não
      implementado"/placeholder para publis — mostram os dados reais ou um estado vazio
      genuíno.
- [x] Testes executados com sucesso via pytest, sem mocks de rede (função 100% local,
      determinística) — 84/84 na suíte completa.

## Notas de Implementação
- **Menção a `@handle` sozinha já conta como indício (`"mencao_marca"`).** Essa é uma
  decisão de produto explícita, não uma inferência de alta confiança: qualquer menção pode
  gerar falso positivo (ex.: perfil marcado só por ter sido fotografado por aquele
  `@handle`, sem nenhuma relação comercial). Optou-se por sinalizar mesmo assim porque o
  objetivo do RF-09 é *mapear candidatos* para revisão humana, não decidir sozinho o que é
  publi — o campo `termos` sempre expõe por que o post foi marcado, permitindo à usuária
  descartar falsos positivos rapidamente na tabela.
- **Sem normalização de acentos nos termos de texto** (`parceria`, `patrocinado`): as
  legendas reais do Instagram nesses termos específicos não carregam ambiguidade de acento
  como o caso "para"/"pará" já tratado em `ISSUE-0002`/`ISSUE-0006`, então `re.IGNORECASE`
  simples é suficiente.
- **Link do post depende de `shortcode` estar presente na legenda coletada.** Isso já é
  garantido para coleta real (`scraper.instaloader_fetch_fn` sempre grava `shortcode`), mas
  posts sem essa informação (ex.: dados legados em cache anterior a esta issue) ainda são
  aceitos pela função — só ficam sem link clicável (`link: None`), a linha na tabela mostra
  o `post_id` como fallback.