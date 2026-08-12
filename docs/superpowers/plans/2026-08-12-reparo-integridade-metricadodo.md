# Reparo de Integridade métricaDODÔ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar a única lacuna real de integridade do métricaDODÔ (RF-09, varredura de publis) e alinhar textos/UX de falha ao contrato exato pedido, sem reintroduzir dados fictícios em execução real.

**Architecture:** `src/filters.py` ganha `detect_sponsored_posts(posts)` (regex sobre legendas). `app.py._run_pipeline` passa a chamar essa função com os posts crus (que já carregam `shortcode`/`caption` via `scraper.instaloader_fetch_fn`) e popula `analysis["publis"]` com itens estruturados (`post_id`, `shortcode`, `link`, `termos`, `marcas`) em vez da lista vazia fixa. `app.py` e `src/exporter.py` deixam de exibir o texto "não implementado" e passam a renderizar a tabela real (ou um estado vazio genuíno). `demo_fetch_fn` ganha legendas (algumas patrocinadas, algumas orgânicas) para que o Modo Demonstração continue validando o pipeline fim-a-fim sem rede. `src/demographics.py`/`data_loaders` já usam a base real do IBGE (1.984 nomes) — só falta um teste de integração explícito provando >80% feminino para os nomes citados no pedido, mais um campo de percentual exposto na UI. A mensagem de falha de coleta (`app.py`) é alinhada ao texto exato pedido.

**Tech Stack:** Python 3, Streamlit, pytest, `re` (stdlib), SQLite, `instaloader`, `google-generativeai`.

## Global Constraints

- Nunca injetar dados fictícios quando "Modo demonstração" estiver desligado e a coleta real falhar — falha deve virar exceção tratada + `st.error` visível, nunca fallback silencioso para `fa_fiel_0`/dados fake. (Já garantido estruturalmente por `scraper.ScraperUnavailableError`; este plano não altera esse contrato, só o texto exibido.)
- Mensagem exata exigida no erro de coleta real: "Falha na coleta do Instagram. Verifique o arquivo de sessão local ou aguarde alguns minutos antes de tentar novamente."
- `detect_sponsored_posts` mora em `src/filters.py` (não em `app.py` nem em módulo novo).
- Padrões de detecção de publi: `#publi`, `#ad`, `parceria`, `patrocinado`, `@marca` (menção via `@handle`).
- Toda a suíte `pytest tests/` deve terminar 100% verde antes de considerar a tarefa concluída.
- Atualizar `PROGRESS.md`, `specs/SPEC-001.md` e `docs/issues/manifest.json` (mais um novo `docs/issues/ISSUE-0007.md` seguindo o padrão dos issues existentes) ao final.
- Não renomear `ScraperUnavailableError` nem mexer no fluxo `NotImplementedError`/`fetch_fn=None` de `src/scraper.py` — ambos já têm testes próprios (`tests/test_scraper.py`) e representam contratos distintos e corretos; o pedido de "exceção clara" já está satisfeito por essa classe.
- `RealGeminiClient` (`src/gemini_analyzer.py`) já lê `GEMINI_API_KEY` via `os.environ.get` e chama a SDK real — nenhuma mudança de código necessária ali, só validação (a suíte já cobre `chunk_into_batches`/`parse_batch_response`/`build_batch_prompt`).

---

### Task 1: `detect_sponsored_posts` em `src/filters.py`

**Files:**
- Modify: `src/filters.py`
- Test: `tests/test_filters.py`

**Interfaces:**
- Produces: `filters.detect_sponsored_posts(posts: list[dict]) -> list[dict]`. Cada `post` de entrada segue o formato já usado em todo o pipeline: `{"post_id": str, "raw": {"caption": str|None, "shortcode": str|None, ...}, ...}`. Cada item de saída: `{"post_id": str, "shortcode": str|None, "link": str|None, "termos": list[str], "marcas": list[str]}`. `link` é `f"https://www.instagram.com/p/{shortcode}/"` quando há `shortcode`, senão `None`. Posts sem legenda (`caption` vazio/ausente) são ignorados (não entram no resultado). Posts com legenda mas sem nenhum indício comercial também são ignorados.

- [ ] **Step 1: Write the failing tests**

```python
def test_detect_sponsored_posts_matches_hashtag_publi():
    posts = [
        {"post_id": "1", "raw": {"shortcode": "abc123", "caption": "Look de hoje #publi com a @marca_x"}},
    ]

    result = filters.detect_sponsored_posts(posts)

    assert len(result) == 1
    assert result[0]["post_id"] == "1"
    assert result[0]["link"] == "https://www.instagram.com/p/abc123/"
    assert "#publi" in result[0]["termos"]
    assert "mencao_marca" in result[0]["termos"]
    assert result[0]["marcas"] == ["marca_x"]


def test_detect_sponsored_posts_matches_ad_hashtag_and_parceria_and_patrocinado():
    posts = [
        {"post_id": "2", "raw": {"shortcode": "sc2", "caption": "Amei esse produto #ad"}},
        {"post_id": "3", "raw": {"shortcode": "sc3", "caption": "Em parceria com a marca"}},
        {"post_id": "4", "raw": {"shortcode": "sc4", "caption": "Post patrocinado pela marca"}},
    ]

    result = filters.detect_sponsored_posts(posts)

    assert {item["post_id"] for item in result} == {"2", "3", "4"}
    by_id = {item["post_id"]: item for item in result}
    assert "#ad" in by_id["2"]["termos"]
    assert "parceria" in by_id["3"]["termos"]
    assert "patrocinado" in by_id["4"]["termos"]


def test_detect_sponsored_posts_ignores_organic_posts():
    posts = [
        {"post_id": "5", "raw": {"shortcode": "sc5", "caption": "Bom dia! Look de hoje, sem parcerias."}},
        {"post_id": "6", "raw": {"caption": None}},
        {"post_id": "7", "raw": {}},
        {"post_id": "8", "raw": None},
    ]

    result = filters.detect_sponsored_posts(posts)

    assert result == []


def test_detect_sponsored_posts_link_is_none_without_shortcode():
    posts = [{"post_id": "9", "raw": {"caption": "Parceria com a marca"}}]

    result = filters.detect_sponsored_posts(posts)

    assert result[0]["link"] is None
    assert result[0]["post_id"] == "9"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_filters.py -q`
Expected: FAIL with `AttributeError: module 'src.filters' has no attribute 'detect_sponsored_posts'`

- [ ] **Step 3: Write minimal implementation**

```python
SPONSORED_PATTERNS = {
    "#publi": re.compile(r"#publi\w*", re.IGNORECASE),
    "#ad": re.compile(r"#ad\b", re.IGNORECASE),
    "parceria": re.compile(r"\bparceria\b", re.IGNORECASE),
    "patrocinado": re.compile(r"\bpatrocinad[oa]\b", re.IGNORECASE),
}
BRAND_MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_.]+)")


def detect_sponsored_posts(posts):
    """RF-09: varre as legendas coletadas em busca de indícios de conteúdo
    comercial (publi/parceria/patrocínio), sem depender de nenhuma chamada
    externa — só regex local sobre o texto já raspado."""
    sponsored = []
    for post in posts:
        raw = post.get("raw") or {}
        caption = raw.get("caption") or ""
        if not caption:
            continue

        termos = [nome for nome, pattern in SPONSORED_PATTERNS.items() if pattern.search(caption)]
        marcas = BRAND_MENTION_PATTERN.findall(caption)
        if marcas:
            termos.append("mencao_marca")

        if not termos:
            continue

        shortcode = raw.get("shortcode")
        sponsored.append(
            {
                "post_id": post.get("post_id"),
                "shortcode": shortcode,
                "link": f"https://www.instagram.com/p/{shortcode}/" if shortcode else None,
                "termos": termos,
                "marcas": marcas,
            }
        )
    return sponsored
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_filters.py -q`
Expected: PASS (todos os testes de `test_filters.py`, incluindo os 4 novos)

- [ ] **Step 5: Commit**

```bash
git add src/filters.py tests/test_filters.py
git commit -m "feat(filters): implementa detect_sponsored_posts (RF-09)"
```

---

### Task 2: Legendas reais no pipeline + Modo Demonstração com publis de exemplo

**Files:**
- Modify: `app.py` (`demo_fetch_fn`, `_run_pipeline`, `PIPELINE_STEPS`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `filters.detect_sponsored_posts(posts)` do Task 1.
- Produces: `analysis["publis"]` deixa de ser `[]` fixo e passa a ser o retorno de `filters.detect_sponsored_posts(posts)` (lista, possivelmente vazia se nada for detectado). `demo_fetch_fn` passa a incluir `"caption"` e `"shortcode"` em `raw` de cada post demo.

- [ ] **Step 1: Write the failing test**

Adicionar em `tests/test_app.py`:

```python
def test_run_pipeline_detects_sponsored_posts_in_demo_mode():
    """RF-09: em Modo Demonstração, ao menos uma publi de exemplo deve ser
    detectada nas legendas geradas localmente (prova de que o pipeline real
    de detecção está conectado, não um placeholder fixo)."""
    import app

    state = {}
    app._run_pipeline("perfil_demo_publis", 90, True, None, state)

    assert state["status"] == "concluido"
    publis = state["analysis"]["publis"]
    assert len(publis) >= 1
    assert all("termos" in item and item["termos"] for item in publis)
    assert all(item["link"] is None or item["link"].startswith("https://www.instagram.com/p/") for item in publis)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app.py::test_run_pipeline_detects_sponsored_posts_in_demo_mode -q`
Expected: FAIL — `publis` ainda vem `[]` fixo de `app.py`.

- [ ] **Step 3: Implementar `demo_fetch_fn` com legendas e `_run_pipeline` chamando `detect_sponsored_posts`**

Em `app.py`, adicionar templates de legenda logo após `DEMO_FIRST_NAMES_M`:

```python
DEMO_CAPTION_TEMPLATES_ORGANIC = [
    "Bom dia! Look de hoje ✨",
    "Feliz com esse ensaio 💛 sem filtro",
]
DEMO_CAPTION_TEMPLATES_SPONSORED = [
    "Parceria com @marca_fashion_demo — usem o cupom DODO10 #publi",
    "Amei esse vestido da @outra_marca_demo, super confortável #ad",
]
```

Em `demo_fetch_fn`, dentro do loop `for i in range(6):`, adicionar antes do `posts.append(...)`:

```python
        is_sponsored = i % 3 == 0
        caption = rng.choice(DEMO_CAPTION_TEMPLATES_SPONSORED if is_sponsored else DEMO_CAPTION_TEMPLATES_ORGANIC)
        shortcode = f"demo{username}{i}"
```

E mudar o `"raw": {"comments": comments}` do post para:

```python
                "raw": {"comments": comments, "caption": caption, "shortcode": shortcode},
```

Em `_run_pipeline`, logo após o bloco que monta `qualified_comments`/`total_comentarios` (antes da etapa `"demografia"`), adicionar:

```python
        publis_detectadas = filters.detect_sponsored_posts(posts)
```

E no dicionário `analysis`, trocar `"publis": [],` por `"publis": publis_detectadas,`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_app.py -q`
Expected: PASS (todos os testes de `test_app.py`, incluindo o novo)

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat(app): conecta detect_sponsored_posts ao pipeline e a legendas do modo demo"
```

---

### Task 3: UI real de publis (`app.py`) e exportador (`src/exporter.py`) sem texto de placeholder

**Files:**
- Modify: `app.py` (`_render_publis_card`)
- Modify: `src/exporter.py` (`PUBLIS_PLACEHOLDER_MSG` → `PUBLIS_VAZIO_MSG`, formatação HTML/PDF de `publis`)
- Test: `tests/test_exporter.py`

**Interfaces:**
- Consumes: itens de `analysis["publis"]` no formato do Task 1 (`post_id`, `shortcode`, `link`, `termos`, `marcas`).
- Produces: `exporter.PUBLIS_VAZIO_MSG` (nova constante pública, substitui `PUBLIS_PLACEHOLDER_MSG`).

- [ ] **Step 1: Write/update the failing tests**

Em `tests/test_exporter.py`, substituir `make_analysis()`'s `"publis": []` fixo não muda (mantém vazio por padrão), mas atualizar os dois testes que hoje assumem placeholder/strings soltas:

```python
def test_generate_html_report_shows_genuine_empty_state_when_no_publis_detected():
    html = exporter.generate_html_report(make_analysis(publis=[]))

    lowered = html.lower()
    assert "publi" in lowered
    # não pode mais dizer que a funcionalidade não foi implementada
    assert "não implementado" not in lowered and "nao implementado" not in lowered
    assert "placeholder" not in lowered
    assert "nenhuma publi" in lowered or "não identificada" in lowered or "nao identificada" in lowered


def test_generate_html_report_lists_real_publis_with_links():
    analysis = make_analysis(
        publis=[
            {
                "post_id": "111",
                "shortcode": "AbC123",
                "link": "https://www.instagram.com/p/AbC123/",
                "termos": ["#publi", "mencao_marca"],
                "marcas": ["marca_x"],
            }
        ]
    )

    html = exporter.generate_html_report(analysis)

    assert "https://www.instagram.com/p/AbC123/" in html
    assert "marca_x" in html


def test_generate_pdf_report_handles_multiple_publis_items():
    """Mesma classe de regressão do teste de gemini_items, para o loop de
    publis — agora com o formato real produzido por detect_sponsored_posts."""
    analysis = make_analysis()
    analysis["publis"] = [
        {"post_id": "1", "shortcode": "a1", "link": "https://www.instagram.com/p/a1/", "termos": ["#publi"], "marcas": ["marca_a"]},
        {"post_id": "2", "shortcode": "a2", "link": "https://www.instagram.com/p/a2/", "termos": ["parceria"], "marcas": ["marca_b"]},
        {"post_id": "3", "shortcode": "a3", "link": "https://www.instagram.com/p/a3/", "termos": ["patrocinado"], "marcas": ["marca_c"]},
    ]

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")
```

Remover o antigo `test_generate_html_report_marks_publis_as_placeholder_when_empty` (substituído pelo teste de empty-state genuíno acima — mesma responsabilidade, contrato novo).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_exporter.py -q`
Expected: FAIL nos 3 testes novos/alterados (mensagem antiga ainda diz "não implementada"; HTML ainda usa `str(item)` para dicts, não link/marca).

- [ ] **Step 3: Implementar em `src/exporter.py`**

Trocar a constante:

```python
PUBLIS_VAZIO_MSG = (
    "Nenhuma publi ou parceria comercial identificada nas legendas coletadas nesta janela."
)
GEMINI_NAO_CONFIGURADO_MSG = "Análise de intenção via Gemini não configurada nesta sessão."
```

Em `generate_html_report`, trocar o bloco de publis:

```python
    publis = analysis.get("publis", []) or []
    if publis:
        publis_html = "".join(
            "<li>"
            + (
                f"<a href=\"{html_lib.escape(str(item.get('link')))}\">{html_lib.escape(str(item.get('link')))}</a>"
                if item.get("link")
                else html_lib.escape(str(item.get("post_id", "")))
            )
            + f" — indícios: {html_lib.escape(', '.join(item.get('termos', [])))}"
            + (f" — marca(s): {html_lib.escape(', '.join(item.get('marcas', [])))}" if item.get("marcas") else "")
            + "</li>"
            for item in publis
        )
    else:
        publis_html = f"<p class='placeholder'>{html_lib.escape(PUBLIS_VAZIO_MSG)}</p>"
```

Em `generate_pdf_report`, trocar o bloco de publis:

```python
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Publis", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "I", 11)
    if publis:
        for item in publis:
            texto = f"- {item.get('link') or item.get('post_id', '')} | indicios: {', '.join(item.get('termos', []))}"
            if item.get("marcas"):
                texto += f" | marca(s): {', '.join(item.get('marcas', []))}"
            pdf.multi_cell(0, 7, _pdf_safe(texto), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 7, _pdf_safe(PUBLIS_VAZIO_MSG))
    pdf.ln(2)
```

- [ ] **Step 4: Atualizar `app.py._render_publis_card` para renderizar a tabela real**

```python
def _render_publis_card(analysis):
    st.subheader("Publis")
    publis = analysis.get("publis", [])
    if not publis:
        st.caption(exporter.PUBLIS_VAZIO_MSG)
        return
    st.table(
        [
            {
                "post": item.get("link") or item.get("post_id"),
                "indícios": ", ".join(item.get("termos", [])),
                "marca(s)": ", ".join(item.get("marcas", [])) or "—",
            }
            for item in publis
        ]
    )
```

E no `main()`, trocar a chamada `_render_publis_card()` (sem argumento) por `_render_publis_card(analysis)`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_exporter.py tests/test_app.py -q`
Expected: PASS em tudo.

- [ ] **Step 6: Commit**

```bash
git add app.py src/exporter.py tests/test_exporter.py
git commit -m "feat(publis): remove placeholder de RF-09 e renderiza publis reais na UI/exportador"
```

---

### Task 4: Mensagem exata de falha de coleta real (sem sugerir fallback fictício)

**Files:**
- Modify: `app.py` (`COLETA_INDISPONIVEL_MSG_TEMPLATE` → `COLETA_INDISPONIVEL_MSG`)
- Test: `tests/test_app.py`

**Interfaces:**
- Produces: `app.COLETA_INDISPONIVEL_MSG` (string fixa, sem `{erro}` interpolado na mensagem principal).

- [ ] **Step 1: Write the failing test**

```python
def test_erro_coleta_indisponivel_shows_exact_required_message(monkeypatch):
    """A mensagem de erro de coleta real deve ser exatamente a exigida — nunca
    deve sugerir 'Modo demonstração' como alternativa a dados reais."""
    import app

    assert app.COLETA_INDISPONIVEL_MSG == (
        "Falha na coleta do Instagram. Verifique o arquivo de sessão local ou "
        "aguarde alguns minutos antes de tentar novamente."
    )
    assert "demonstra" not in app.COLETA_INDISPONIVEL_MSG.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app.py::test_erro_coleta_indisponivel_shows_exact_required_message -q`
Expected: FAIL — `AttributeError: module 'app' has no attribute 'COLETA_INDISPONIVEL_MSG'`

- [ ] **Step 3: Implementar em `app.py`**

Substituir a constante:

```python
COLETA_INDISPONIVEL_MSG = (
    "Falha na coleta do Instagram. Verifique o arquivo de sessão local ou "
    "aguarde alguns minutos antes de tentar novamente."
)
```

E no `main()`, trocar:

```python
    elif status == "erro_coleta_indisponivel":
        st.error(COLETA_INDISPONIVEL_MSG_TEMPLATE.format(erro=state.get("erro", "erro desconhecido")))
```

por:

```python
    elif status == "erro_coleta_indisponivel":
        st.error(COLETA_INDISPONIVEL_MSG)
        st.caption(f"Detalhe técnico: {state.get('erro', 'erro desconhecido')}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_app.py -q`
Expected: PASS em tudo.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "fix(app): alinha mensagem de falha de coleta ao texto exato exigido, sem sugerir modo demo"
```

---

### Task 5: Prova de integração do engine demográfico real (IBGE) + percentual exposto na UI

**Files:**
- Modify: `app.py` (`_genero_predominante` ganha vizinho `_genero_percentuais`, `_run_pipeline`, `_render_demografia_card`)
- Test: `tests/test_demographics.py`, `tests/test_app.py`

**Interfaces:**
- Produces: `analysis["demografia"]["genero_pct"] = {"feminino": float, "masculino": float, "indeterminado": float}` (frações 0.0–1.0, somando 1.0 quando há pelo menos um comentário).

- [ ] **Step 1: Write the failing tests**

Em `tests/test_demographics.py`, adicionar (usando a base real, não uma `CUSTOM_NAMES_DB` sintética):

```python
from src import data_loaders

FEMALE_NAMES_FROM_SPEC = ["Maria", "Ana", "Camila", "Fernanda", "Juliana", "Patricia", "Sofia"]


def test_infer_gender_classifies_spec_female_names_as_feminino_using_real_ibge_base():
    names_db = data_loaders.load_names_db()

    for nome in FEMALE_NAMES_FROM_SPEC:
        assert demographics.infer_gender(nome, names_db=names_db) == "feminino", nome


def test_infer_gender_female_ratio_above_80_percent_for_spec_names_using_real_ibge_base():
    names_db = data_loaders.load_names_db()

    for nome in FEMALE_NAMES_FROM_SPEC:
        counts = names_db[demographics._normalize_name(nome)]
        total = counts["F"] + counts["M"]
        assert counts["F"] / total > 0.80, nome
```

Em `tests/test_app.py`, adicionar:

```python
def test_run_pipeline_exposes_genero_pct_in_demo_mode():
    import app

    state = {}
    app._run_pipeline("perfil_demo_genero", 90, True, None, state)

    assert state["status"] == "concluido"
    genero_pct = state["analysis"]["demografia"]["genero_pct"]
    assert set(genero_pct.keys()) == {"feminino", "masculino", "indeterminado"}
    assert abs(sum(genero_pct.values()) - 1.0) < 1e-9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_demographics.py tests/test_app.py -q`
Expected: FAIL — `genero_pct` ainda não existe em `analysis["demografia"]`.

- [ ] **Step 3: Implementar em `app.py`**

Adicionar logo abaixo de `_genero_predominante`:

```python
def _genero_percentuais(contagem):
    total = sum(contagem.values())
    if total == 0:
        return {"feminino": 0.0, "masculino": 0.0, "indeterminado": 0.0}
    return {chave: valor / total for chave, valor in contagem.items()}
```

No `analysis["demografia"]` dentro de `_run_pipeline`, adicionar a chave:

```python
            "demografia": {
                "genero_predominante": _genero_predominante(genero_contagem),
                "genero_pct": _genero_percentuais(genero_contagem),
                "regioes": regioes,
            },
```

Em `_render_demografia_card`:

```python
def _render_demografia_card(analysis):
    st.subheader("Demografia da audiência")
    demografia = analysis["demografia"]
    pct_feminino = demografia.get("genero_pct", {}).get("feminino", 0.0) * 100
    st.write(f"**Gênero predominante:** {demografia['genero_predominante']} ({pct_feminino:.1f}% feminino na amostra)")
    regioes = demografia["regioes"]
    st.write(f"**Regiões detectadas:** {', '.join(regioes) if regioes else 'Nenhuma região detectada'}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_demographics.py tests/test_app.py -q`
Expected: PASS em tudo.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_demographics.py tests/test_app.py
git commit -m "test(demographics): prova integração com base real do IBGE e expõe genero_pct na UI"
```

---

### Task 6: Suíte completa verde + atualização de documentação

**Files:**
- Modify: `PROGRESS.md`, `specs/SPEC-001.md`, `docs/issues/manifest.json`
- Create: `docs/issues/ISSUE-0007.md`

**Interfaces:**
- Nenhuma interface de código nova — só documentação, seguindo o padrão dos arquivos `docs/issues/ISSUE-000{1..6}.md` já existentes (seções `## Objetivo`, `## Tarefas de Implementação`, `## Critérios de Aceite (Definition of Done)`, `## Notas de Implementação`).

- [ ] **Step 1: Run the full suite one last time**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: 100% dos testes passando (baseline era 74 passed; após as Tasks 1–5 o total sobe pelos testes novos listados acima).

- [ ] **Step 2: Criar `docs/issues/ISSUE-0007.md`**

Seguir o template dos issues existentes (ver `docs/issues/ISSUE-0005.md` como referência de estrutura), documentando: objetivo (RF-09), a função `detect_sponsored_posts`, os padrões de regex usados, o formato de item retornado, e a decisão de que menção a `@handle` sozinha já conta como indício (`mencao_marca`) — decisão de produto que pode gerar falsos positivos (ex.: perfil marcado só por ter sido fotografado por ele), registrada explicitamente como trade-off conhecido.

- [ ] **Step 3: Atualizar `docs/issues/manifest.json`**

Adicionar entrada `ISSUE-0007` com `status: "concluida"` e nota reaproveitando o texto do passo anterior; atualizar a nota de `ISSUE-0004` removendo a frase "RF-09 (publis) segue placeholder explícito, fora do escopo desta issue" (a issue-mãe não muda de status, só o comentário sobre a pendência que agora foi resolvida em outro issue).

- [ ] **Step 4: Atualizar `specs/SPEC-001.md`**

Na tabela da seção 4, trocar a linha de `RF-09` de `Não implementado` para `Feito`, com issue `ISSUE-0007` e observação curta apontando os padrões de regex e o trade-off de `mencao_marca`.

- [ ] **Step 5: Atualizar `PROGRESS.md`**

Adicionar bullet `[x] **ISSUE-0007**` na seção "Status Atual" nos mesmos moldes das entradas existentes; atualizar a contagem de testes na seção "Testes" (novo total real, medido no Step 1); remover o item 3 ("Varredura de publis (RF-09) — sem issue própria aberta ainda") da lista "O que falta para sair de 'demonstração' para uso real", já que deixou de ser uma pendência.

- [ ] **Step 6: Commit**

```bash
git add PROGRESS.md specs/SPEC-001.md docs/issues/manifest.json docs/issues/ISSUE-0007.md
git commit -m "docs: registra ISSUE-0007 (RF-09 publis) e atualiza status do SPEC-001/PROGRESS"
```

---

## Self-Review

- **Cobertura do pedido:** item 1 (sem mock em execução real) → já garantido estruturalmente, Task 4 alinha só o texto da mensagem; item 2 (engine demográfico/IBGE) → já estava correto no caminho real, Task 5 prova isso com teste de integração e expõe o percentual; item 3 (Gemini real) → já implementado, sem tarefa de código (nenhuma mudança necessária); item 4 (RF-09) → Tasks 1–3, é o núcleo do trabalho; item 5 (TDD + manifesto) → Task 6.
- **Placeholders:** nenhum "TBD"/"implementar depois" — todo passo tem código completo ou comando exato.
- **Consistência de tipos:** `detect_sponsored_posts` (Task 1) devolve exatamente o shape consumido por `_render_publis_card` (Task 3) e pelos formatadores do `exporter.py` (Task 3) — `post_id`, `shortcode`, `link`, `termos`, `marcas` usados de forma idêntica em todos os pontos.

---

**Execução:** dado que a análise completa do código já foi feita nesta mesma sessão (todo o contexto necessário já está carregado), vou seguir com **execução inline** (`superpowers:executing-plans`) em vez de subagentes — evita reprocessar contexto que já tenho, e o escopo é pequeno o suficiente para não precisar dos checkpoints de revisão entre agentes.
