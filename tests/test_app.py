import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

from src import database

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


class _FakeGeminiResponse:
    def __init__(self, text):
        self.text = text


class _FakeGeminiClient:
    """Client Gemini fake com o mesmo contrato duck-typed (generate_content ->
    objeto com .text) usado por analyze_batch, para testar os agregados novos
    de summarize_brand_suitability sem chamar a API real."""

    def __init__(self, response_text, *args, **kwargs):
        self.response_text = response_text

    def generate_content(self, prompt):
        return _FakeGeminiResponse(self.response_text)


_FAKE_GEMINI_RESPONSE_TEXT = (
    '[{"comentario": "Qual o preço desse vestido?", "intencao_compra": "alta", '
    '"faixa_etaria_estimada": "18-24", "categoria_sentimento": "interesse_comercial", '
    '"sinais_compra": ["preco"]}, '
    '{"comentario": "Vocês têm no tamanho M?", "intencao_compra": "media", '
    '"faixa_etaria_estimada": "18-24", "categoria_sentimento": "interesse_comercial", '
    '"sinais_compra": ["tamanho"]}]'
)


def _fake_qualified_shallow_cached():
    def comentario(username, texto):
        return {"username": username, "texto": texto, "respondido": False}

    return {
        "profile": {"followers_count": 5000},
        "posts": [
            {
                "post_id": "1",
                "likes_count": 100,
                "comments_count": 3,
                "raw": {
                    "shortcode": "sc1",
                    "caption": "look de hoje",
                    "comments": [
                        comentario("maria_style", "Qual o preço desse vestido?"),
                        comentario("ana_looks", "Vocês têm no tamanho M?"),
                        comentario("pedro99", "Lindo"),
                    ],
                },
            },
        ],
    }


def test_app_boots_without_exception():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception


def test_app_has_main_input_widgets():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    # RF-01: input de perfil/URL
    assert len(at.text_input) >= 1
    # RF-02: seletor de janela 30/60/90 dias
    assert len(at.selectbox) >= 1
    assert list(at.selectbox[0].options) == [30, 60, 90] or "30" in [
        str(o) for o in at.selectbox[0].options
    ]
    # botão de disparo do pipeline
    button_labels = [b.label for b in at.button]
    assert any("Analisar" in label for label in button_labels)


def test_app_has_demo_mode_toggle():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    # Modo demonstração — coexiste com raspagem real ainda não implementada (ISSUE-0001)
    assert len(at.toggle) >= 1
    toggle_labels = [t.label for t in at.toggle]
    assert any("emonstra" in label for label in toggle_labels)


def test_app_idle_state_shows_no_analysis_yet():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    # Sem clique em "Analisar", não deve haver botões de download de relatório
    download_button_labels = [b.label for b in at.download_button]
    assert download_button_labels == []


def test_sidebar_shows_active_session_when_session_file_detected(monkeypatch):
    from src import scraper

    monkeypatch.setattr(scraper, "detect_available_session_username", lambda: "criativododo")

    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    sidebar_success_values = [s.value for s in at.sidebar.success]
    assert any("criativododo" in value for value in sidebar_success_values)


def test_sidebar_warns_when_no_session_file_detected(monkeypatch):
    from src import scraper

    monkeypatch.setattr(scraper, "detect_available_session_username", lambda: None)

    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    sidebar_warning_values = [w.value for w in at.sidebar.warning]
    assert any("sess" in value.lower() for value in sidebar_warning_values)


def test_app_has_limpar_cache_button():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    button_labels = [b.label for b in at.button]
    assert any("Limpar Cache e Re-analisar Perfil" in label for label in button_labels)


def test_limpar_cache_button_clears_cached_profile_before_reanalyzing(monkeypatch):
    """O botão 'Limpar Cache e Re-analisar Perfil' deve apagar o cache do
    perfil antes de disparar o pipeline, garantindo que registros antigos ou
    corrompidos (ex.: fa_fiel_0) não sobrevivam à re-análise. A raspagem (mesmo
    em modo demo) reescreve o cache em thread de background logo em seguida,
    então o que a UI garante é a ORDEM (limpar antes de iniciar), verificada
    aqui via monkeypatch em vez de inspecionar o cache.db pós-clique (que teria
    corrida com a thread de background). Usa `src.database` diretamente (não
    `import app`): importar `app` executa `main()` em modo bare (fora de um
    ScriptRunContext real), o que deixa lixo de estado de formulário do
    Streamlit entre testes e quebra AppTest.from_file() chamado depois."""
    from src import database

    calls = []
    monkeypatch.setattr(database, "clear_profile_cache", lambda username: calls.append(username))

    username = f"perfil_limpar_cache_{uuid.uuid4().hex}"

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(username)
    at.toggle(key="demo_mode_toggle").set_value(True)
    limpar_button = next(b for b in at.button if b.label == "Limpar Cache e Re-analisar Perfil")
    limpar_button.click().run()

    assert not at.exception
    assert calls == [username]

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert at.session_state["pipeline_state"]["status"] == "concluido"


def test_app_demo_pipeline_runs_end_to_end_without_gemini_api_key(monkeypatch):
    """Sem GEMINI_API_KEY no ambiente, o Modo Demonstração continua funcionando
    fim-a-fim: RealGeminiClient() levanta RuntimeError, app.py deve capturar isso
    e seguir sem chamar o Gemini real. Desde a decisão de produto de 13/08/2026,
    o Modo Demonstração injeta DemoGeminiClient (fake, sem rede/custo) em vez de
    None, então gemini_configurado passa a ser True — é isso que permite a seção
    "Insights acionáveis de campanha" aparecer em demonstração sem chave real."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    at.text_input(key="username_input").set_value("perfil_demo_teste")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    # Pipeline roda em thread de background; drena o polling síncrono do AppTest
    # até concluir (ou falhar), sem nunca bloquear além do necessário para o teste.
    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "concluido"
    assert at.session_state["pipeline_state"]["gemini_configurado"] is True


def test_app_demo_mode_renders_campaign_insights_section_without_gemini_api_key(monkeypatch):
    """A seção "Insights acionáveis de campanha" (incluindo os cards Top 3 por
    alcance/volume e Top 3 por qualidade/conversão, com PostScore_i canônico)
    deve renderizar em tela no Modo Demonstração mesmo sem GEMINI_API_KEY —
    condição de aceite da decisão de produto de 13/08/2026 de habilitar
    DemoGeminiClient nesse modo."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    at.text_input(key="username_input").set_value(f"perfil_demo_insights_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "concluido"
    assert at.session_state["pipeline_state"]["gemini_configurado"] is True

    subheader_values = [s.value for s in at.subheader]
    assert "Insights acionáveis de campanha" in subheader_values

    markdown_values = [m.value for m in at.markdown]
    assert any("Top 3 por alcance/volume" in v for v in markdown_values)
    assert any("Top 3 por qualidade/conversão" in v for v in markdown_values)

    campaign_insights = at.session_state["pipeline_state"]["analysis"]["campaign_insights"]
    assert campaign_insights is not None
    assert len(campaign_insights["top_3_by_quality"]) <= 3
    assert all(0.0 <= post["post_score"] <= 1.0 for post in campaign_insights["top_3_by_quality"])


def test_app_demo_mode_renders_content_affinity_cards(monkeypatch):
    """Sprint 002 Fase 4: os cards "Top 3 Posts", "Hashtags populares" e
    "Menções de marcas" devem renderizar de fato na tela (via AppTest, não só
    chamada direta da função) ao final de um fluxo real de Modo
    Demonstração, já que demo_fetch_fn sempre gera posts patrocinados com
    hashtags e menções (i % 3 == 0, determinístico)."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    at.text_input(key="username_input").set_value(f"perfil_demo_conteudo_ui_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "concluido"

    subheader_values = [s.value for s in at.subheader]
    assert "Top 3 Posts" in subheader_values
    assert "Hashtags populares" in subheader_values
    assert "Menções de marcas" in subheader_values


def test_app_renders_provenance_card_with_status_per_engagement_rate(monkeypatch):
    """Card 'Proveniência e Escopo das Métricas' (Sprint 002 Fase 3,
    BENCHMARK-001.md §5.2): em Modo Demonstração, engagement_rate_by_followers
    e engagement_rate_by_views (há Reels na amostra demo) devem aparecer como
    'Disponível', e engagement_rate_by_reach (demo não gera estimated_reach)
    como 'Indisponível' — prova de que os badges refletem o status real do
    audit_report, não um valor fixo."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    at.text_input(key="username_input").set_value(f"perfil_demo_provenance_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "concluido"

    subheader_values = [s.value for s in at.subheader]
    assert "Proveniência e Escopo das Métricas" in subheader_values

    markdown_values = " ".join(m.value for m in at.markdown)
    assert "Por seguidores" in markdown_values and "Disponível" in markdown_values
    assert "Por alcance" in markdown_values and "Indisponível" in markdown_values
    assert "Por views de Reels" in markdown_values

    caption_values = " ".join(c.value for c in at.caption)
    assert "vídeo" in caption_values.lower() or "reel" in caption_values.lower()


def test_app_renders_new_audience_metric_cards_when_gemini_configured(monkeypatch):
    """Quando o Gemini está configurado, a UI deve exibir os agregados de
    audiência (taxa de comentários qualificados, distribuição de intenção de
    compra, sentimento e faixa etária predominante), não só a tabela crua
    item-a-item do Gemini. Patcheia `src.gemini_analyzer.RealGeminiClient`
    diretamente (não `import app`) para não disparar o `main()` em modo bare
    do módulo `app` e quebrar `AppTest.from_file()` por lixo de estado de
    formulário entre testes (ver nota em test_limpar_cache_button_...)."""
    from src import gemini_analyzer, scraper

    monkeypatch.setattr(scraper, "scrape_profile", lambda *args, **kwargs: _fake_qualified_shallow_cached())
    monkeypatch.setattr(
        gemini_analyzer, "RealGeminiClient", lambda *args, **kwargs: _FakeGeminiClient(_FAKE_GEMINI_RESPONSE_TEXT)
    )

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_gemini_ui_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(False)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "concluido"
    assert at.session_state["pipeline_state"]["gemini_configurado"] is True

    markdown_values = " ".join(m.value for m in at.markdown)
    assert "Distribuição de intenção de compra" in markdown_values
    assert "Sentimento dos comentários" in markdown_values
    assert "Faixa etária predominante da audiência" in markdown_values
    assert "18-24" in markdown_values

    metric_labels = [m.label for m in at.metric]
    assert any("qualificados" in label.lower() for label in metric_labels)


def test_app_shows_safety_message_when_pipeline_reports_pausado_seguranca(monkeypatch):
    # AppTest-based: precisa ficar ANTES do bloco de testes que fazem `import app`
    # bare (a partir daqui para baixo) — import bare roda main() fora de um
    # ScriptRunContext real e deixa lixo de estado de formulário do Streamlit,
    # quebrando qualquer AppTest.from_file() chamado depois (ver nota em
    # test_limpar_cache_button_clears_cached_profile_before_reanalyzing).
    from src import rate_controller, scraper

    def _raise_safe_stop(*args, **kwargs):
        raise rate_controller.SafeStop(reason="http_429")

    monkeypatch.setattr(scraper, "scrape_profile", _raise_safe_stop)

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_safe_stop_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(False)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "pausado_seguranca"
    warning_values = [w.value for w in at.warning]
    assert any(rate_controller.SAFETY_MESSAGE in value for value in warning_values)


def test_app_hides_export_buttons_until_ver_relatorio_clicked():
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_ver_relatorio_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert at.session_state["pipeline_state"]["status"] == "concluido"
    assert at.download_button == []
    ver_relatorio_button = next(b for b in at.button if b.label == "Ver Relatório")

    ver_relatorio_button.click().run()

    assert not at.exception
    assert len(at.download_button) >= 1


def test_app_full_demo_flow_renders_title_sidebar_and_both_export_buttons(monkeypatch):
    """Sanity check de fechamento da Sprint 002: título, sidebar de sessão do
    Instagram, badge de Modo Demonstração e os dois botões de exportação
    (HTML e PDF, não mais 'JSON' — texto desatualizado corrigido nesta rodada)
    devem aparecer sem exceção ao final do fluxo real Analisar -> Ver
    Relatório."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception
    assert at.title[0].value == "métricaDODÔ"
    sidebar_subheader_values = [s.value for s in at.sidebar.subheader]
    assert "Sessão do Instagram" in sidebar_subheader_values

    at.text_input(key="username_input").set_value(f"perfil_fechamento_sprint002_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "concluido"
    info_values = [i.value for i in at.info]
    assert any("MODO DEMONSTRAÇÃO" in value for value in info_values)

    success_values = [s.value for s in at.success]
    assert any("HTML/PDF" in value for value in success_values)
    assert not any("JSON" in value for value in success_values)

    next(b for b in at.button if b.label == "Ver Relatório").click().run()

    assert not at.exception
    download_labels = sorted(b.label for b in at.download_button)
    assert download_labels == ["Baixar relatório (HTML)", "Baixar relatório (PDF)"]


def test_app_gerar_novo_relatorio_resets_screen_without_clearing_cache(monkeypatch):
    from src import database

    clear_cache_calls = []
    monkeypatch.setattr(database, "clear_profile_cache", lambda username: clear_cache_calls.append(username))

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_gerar_novo_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    next(b for b in at.button if b.label == "Ver Relatório").click().run()
    next(b for b in at.button if b.label == "Gerar novo relatório").click().run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "ocioso"
    assert at.session_state["mostrar_relatorio"] is False
    assert clear_cache_calls == []


def test_run_pipeline_detects_sponsored_posts_in_demo_mode():
    """RF-09: em Modo Demonstração, ao menos uma publi de exemplo deve ser
    detectada nas legendas geradas localmente (prova de que o pipeline real
    de detecção está conectado, não um placeholder fixo)."""
    import app

    # Username único: scrape_profile usa o cache SQLite compartilhado
    # (database.DB_PATH) por padrão, e um username fixo colidiria com cache
    # de execuções anteriores deste mesmo teste.
    username = f"perfil_demo_publis_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, True, None, state)

    assert state["status"] == "concluido"
    publis = state["analysis"]["publis"]
    assert len(publis) >= 1
    assert all("termos" in item and item["termos"] for item in publis)
    assert all(item["link"] is None or item["link"].startswith("https://www.instagram.com/p/") for item in publis)


def test_render_provenance_card_never_raises_without_audit_report():
    """analyses geradas antes da Sprint 002 Fase 2 (ou qualquer falha ao
    computar build_audit_report) não têm `audit_report` — o card precisa
    degradar graciosamente em vez de lançar KeyError/TypeError."""
    import app

    app._render_provenance_card({"username": "perfil_sem_audit_report"})
    app._render_provenance_card({"username": "perfil_audit_report_vazio", "audit_report": {}})
    app._render_provenance_card({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}})


def test_run_pipeline_attaches_canonical_audit_report_with_reels_views_in_demo_mode():
    """Sprint 002 Fase 2: build_audit_report() deve ser anexado a
    analysis["audit_report"], com engagement_rate_by_views calculável no
    Modo Demonstração (demo_fetch_fn gera Reels com video_view_count) —
    prova de que o contrato canônico está de fato ligado ao pipeline real,
    não só testado isoladamente em tests/test_metrics.py."""
    import app

    username = f"perfil_demo_audit_report_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, True, None, state)

    assert state["status"] == "concluido"
    audit_report = state["analysis"]["audit_report"]
    assert set(audit_report.keys()) == {"metrics", "provenance"}

    by_followers = audit_report["metrics"]["engagement_rate_by_followers"]
    assert by_followers["status"] == "ok"
    assert isinstance(by_followers["value"], float)

    by_views = audit_report["metrics"]["engagement_rate_by_views"]
    assert by_views["status"] == "ok"
    assert isinstance(by_views["value"], float)

    # engagement_rate legado (float simples) continua intocado.
    assert isinstance(state["analysis"]["engagement_rate"], float)

    cached = database.get_cached_data(username, window_days=90, source="demo")
    assert cached["audit_report"] == audit_report


def test_run_pipeline_exposes_genero_pct_in_demo_mode():
    import app

    username = f"perfil_demo_genero_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, True, None, state)

    assert state["status"] == "concluido"
    genero_pct = state["analysis"]["demografia"]["genero_pct"]
    assert set(genero_pct.keys()) == {"feminino", "masculino", "indeterminado"}
    assert abs(sum(genero_pct.values()) - 1.0) < 1e-9


# --- Sprint 002 Fase 4: Top Posts / Hashtags / Menções / demografia com cobertura


def test_run_pipeline_attaches_top_posts_popular_tags_and_brand_mentions_in_demo_mode():
    """Modo Demonstração (demo_fetch_fn) sempre gera pelo menos 2 posts
    'patrocinados' (is_sponsored = i % 3 == 0, determinístico) com hashtags
    (#publi/#ad) e menções (@marca_fashion_demo/@outra_marca_demo) nas
    legendas — prova de que o contrato canônico de conteúdo (Sprint 002
    Fase 4) está de fato ligado ao pipeline real."""
    import app

    username = f"perfil_demo_conteudo_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, True, None, state)

    assert state["status"] == "concluido"
    audit_metrics = state["analysis"]["audit_report"]["metrics"]

    top_posts = audit_metrics["top_posts"]
    assert top_posts["status"] == "ok"
    assert len(top_posts["posts"]) >= 1
    assert all(item["link"].startswith("https://www.instagram.com/p/") for item in top_posts["posts"])

    popular_tags = audit_metrics["popular_tags"]
    assert popular_tags["status"] == "ok"
    assert any(tag["tag"] in {"#publi", "#ad"} for tag in popular_tags["tags"])

    brand_mentions = audit_metrics["brand_mentions"]
    assert brand_mentions["status"] == "ok"
    assert any(item["tipo"] == "publi_confirmada" for item in brand_mentions["mentions"])


def test_run_pipeline_attaches_gender_and_region_distribution_with_coverage_in_demo_mode():
    import app

    username = f"perfil_demo_demografia_fase4_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, True, None, state)

    assert state["status"] == "concluido"
    audit_metrics = state["analysis"]["audit_report"]["metrics"]

    gender_metric = audit_metrics["gender_distribution"]
    assert gender_metric["status"] == "ok"
    assert gender_metric["unit"] == "percent"
    assert 0.0 <= gender_metric["value"] <= 100.0
    assert any("amostragem" in r for r in gender_metric["ressalvas"])

    region_metric = audit_metrics["region_distribution"]
    assert region_metric["status"] == "ok"
    assert region_metric["unit"] == "percent"


def test_render_top_posts_card_never_raises_without_audit_report():
    import app

    app._render_top_posts_card({"username": "perfil_sem_audit_report"})
    app._render_top_posts_card({"username": "perfil_audit_report_vazio", "audit_report": {}})
    app._render_top_posts_card({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}})


def test_render_popular_tags_card_never_raises_without_audit_report():
    import app

    app._render_popular_tags_card({"username": "perfil_sem_audit_report"})
    app._render_popular_tags_card({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}})


def test_render_brand_mentions_card_never_raises_without_audit_report():
    import app

    app._render_brand_mentions_card({"username": "perfil_sem_audit_report"})
    app._render_brand_mentions_card({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}})


def test_render_demografia_card_never_raises_without_audit_report():
    import app

    analysis = {
        "username": "perfil_sem_audit_report",
        "demografia": {"genero_predominante": "indeterminado", "genero_pct": {}, "regioes": []},
    }
    app._render_demografia_card(analysis)


def test_run_pipeline_returns_proportional_region_breakdown_and_handles_prefixed_gender_in_real_mode(monkeypatch):
    """RF: perfis femininos de moda/lifestyle devem classificar a amostragem
    como predominantemente feminina (>80%) mesmo com @handles prefixados
    ('style_by_...'), e a lista de regiões deve vir proporcional
    ('SP (40%), RJ (25%)...') em vez de um único estado ou lista sem peso."""
    import app

    def comentario(username, texto):
        return {"username": username, "texto": texto, "respondido": False}

    fake_cached = {
        "profile": {"followers_count": 20000},
        "posts": [
            {
                "post_id": "1",
                "likes_count": 100,
                "comments_count": 10,
                "raw": {
                    "shortcode": "sc1",
                    "caption": "look de hoje",
                    "comments": [
                        comentario("style_by_maria", "chama no (11) 91234-5678"),
                        comentario("its_ana_oficial", "chama no (11) 98765-4321"),
                        comentario("camila.moda92", "moro no Rio de Janeiro"),
                        comentario("eu_juliana_looks", "sou de Minas Gerais"),
                        comentario("look.by.patricia", "Lindo"),
                    ],
                },
            },
        ],
    }

    monkeypatch.setattr(app.scraper, "scrape_profile", lambda *args, **kwargs: fake_cached)

    state = {}
    app._run_pipeline("perfil_moda_teste", 90, False, None, state)

    assert state["status"] == "concluido"
    analysis = state["analysis"]
    demografia = analysis["demografia"]

    # >80% feminino mesmo com handles prefixados (style_by_, its_..._oficial, eu_..._looks, look.by.)
    assert demografia["genero_predominante"] == "feminino"
    assert demografia["genero_pct"]["feminino"] > 0.8

    # lista proporcional (não um único estado): 2 detecções de SP, 1 de RJ, 1 de MG
    assert demografia["regioes"] == ["SP (50%)", "RJ (25%)", "MG (25%)"]


def test_run_pipeline_filters_posts_outside_window_and_infers_gender_from_handle_in_real_mode(monkeypatch):
    """Prova de integração do reparo de ancoragem na realidade física: em modo
    real (demo_mode=False), posts fora da janela selecionada não devem
    contribuir para as métricas, e o gênero deve ser inferido a partir do
    @handle do comentarista quando não há 'nome' explícito — comentários
    reais (via instaloader_fetch_fn) só trazem 'username', nunca 'nome'."""
    import datetime as dt

    import app

    recent_date = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=5)).isoformat()
    old_date = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=200)).isoformat()

    fake_cached = {
        "profile": {"followers_count": 10000},
        "posts": [
            {
                "post_id": "1",
                "likes_count": 100,
                "comments_count": 1,
                "raw": {
                    "shortcode": "sc1",
                    "caption": "look de hoje",
                    "published_at": recent_date,
                    "comments": [{"username": "ana_silva92", "texto": "Quanto custa?", "respondido": False}],
                },
            },
            {
                "post_id": "2",
                "likes_count": 999,
                "comments_count": 5,
                "raw": {
                    "shortcode": "sc2",
                    "caption": "look antigo",
                    "published_at": old_date,
                    "comments": [{"username": "joao99", "texto": "Top", "respondido": False}],
                },
            },
        ],
    }

    monkeypatch.setattr(app.scraper, "scrape_profile", lambda *args, **kwargs: fake_cached)

    state = {}
    app._run_pipeline("perfil_real_teste", 90, False, None, state)

    assert state["status"] == "concluido"
    analysis = state["analysis"]
    # post de 200 dias atrás está fora da janela de 90 dias -> não conta nas métricas
    assert analysis["comentarios_analisados"]["total"] == 1
    # gênero inferido a partir do handle 'ana_silva92' -> 'ana' -> feminino
    assert analysis["demografia"]["genero_predominante"] == "feminino"


def test_run_pipeline_e2e_with_simulated_real_instagram_profile(monkeypatch):
    """E2E: simula a API real do Instaloader (sem rede) e roda o pipeline
    completo (demo_mode=False) fim-a-fim — instaloader_fetch_fn -> cache SQLite
    -> app._run_pipeline -> analysis. Prova que os dois reparos (comentários
    reais + janela por data de publicação) se conectam corretamente de ponta
    a ponta, não só isoladamente por módulo."""
    import datetime as dt

    import app
    from src import scraper

    class FakeOwner:
        def __init__(self, username):
            self.username = username

    class FakeComment:
        def __init__(self, owner_username, text):
            self.owner = FakeOwner(owner_username)
            self.text = text
            self.answers = []

    class FakePost:
        def __init__(self, mediaid, shortcode, caption, likes, comments_count, date_utc, comments):
            self.mediaid = mediaid
            self.shortcode = shortcode
            self.caption = caption
            self.likes = likes
            self.comments = comments_count
            self.date_utc = date_utc
            self._comments = comments

        def get_comments(self):
            return iter(self._comments)

    recent = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=5)
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=200)

    recent_comments = [
        FakeComment("camila_style23", "Qual o preço desse vestido?"),
        FakeComment("fernanda.looks", "Vocês têm no tamanho M?"),
        FakeComment("pedro99_", "Lindo"),
    ]
    old_comments = [FakeComment("joao_antigo", "Top")]

    class FakeProfile:
        username = "perfil_real_e2e"
        biography = "bio real"
        followers = 8000

        @staticmethod
        def get_posts():
            return iter(
                [
                    FakePost(1, "recente", "look novo #publi @marca_parceira", 300, 3, recent, recent_comments),
                    FakePost(2, "antigo", "look antigo", 50, 1, old, old_comments),
                ]
            )

    class FakeContext:
        pass

    class FakeInstaloader:
        def __init__(self):
            self.context = FakeContext()

        def load_session_from_file(self, username, filename):
            pass

    monkeypatch.setattr(scraper.instaloader, "Instaloader", FakeInstaloader)
    monkeypatch.setattr(
        scraper.instaloader.Profile,
        "from_username",
        staticmethod(lambda context, username: FakeProfile()),
    )

    username = f"perfil_real_e2e_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, False, None, state)

    assert state["status"] == "concluido"
    analysis = state["analysis"]

    # post de 200 dias atrás está fora da janela de 90 dias -> só o post recente conta
    assert analysis["comentarios_analisados"]["total"] == 3
    # 2 comentaristas femininas ("camila", "fernanda") vs 1 masculino ("pedro") -> feminino
    assert analysis["demografia"]["genero_predominante"] == "feminino"
    assert analysis["demografia"]["genero_pct"]["feminino"] > 0.5
    # TER calculada só sobre o post dentro da janela (300 likes + 3 comments / 8000 seguidores)
    assert analysis["engagement_rate"] == (300 + 3) / 8000
    # publi detectada na legenda do post recente (RF-09)
    assert len(analysis["publis"]) == 1
    assert analysis["publis"][0]["link"] == "https://www.instagram.com/p/recente/"


def test_erro_coleta_indisponivel_shows_exact_required_message():
    """A mensagem de erro de coleta real deve ser exatamente a exigida — nunca
    deve sugerir 'Modo demonstração' como alternativa a dados reais."""
    import app

    assert app.COLETA_INDISPONIVEL_MSG == (
        "Falha na coleta do Instagram. Verifique o arquivo de sessão local ou "
        "aguarde alguns minutos antes de tentar novamente."
    )
    assert "demonstra" not in app.COLETA_INDISPONIVEL_MSG.lower()


def test_run_pipeline_sets_erro_coleta_indisponivel_status(monkeypatch):
    """scraper.ScraperUnavailableError deve virar um status tratado na UI, nunca
    uma exceção crua propagada pela thread de background."""
    import app

    def fake_scrape_profile(*args, **kwargs):
        raise app.scraper.ScraperUnavailableError("sem rede e sem cache neste teste")

    monkeypatch.setattr(app.scraper, "scrape_profile", fake_scrape_profile)

    state = {}
    app._run_pipeline("perfil_sem_cache", 90, False, None, state)

    assert state["status"] == "erro_coleta_indisponivel"


def test_run_pipeline_exposes_new_brand_suitability_aggregates_with_fake_gemini_client(monkeypatch):
    """O pipeline deve propagar os novos agregados de summarize_brand_suitability
    (distribuicao_intencao_compra e faixa_etaria_predominante) até o parecer
    comercial exposto em analysis, para consumo pela UI e pelo exportador."""
    import app

    monkeypatch.setattr(app.scraper, "scrape_profile", lambda *args, **kwargs: _fake_qualified_shallow_cached())

    gemini_client = _FakeGeminiClient(_FAKE_GEMINI_RESPONSE_TEXT)
    state = {}
    app._run_pipeline("perfil_agregados_teste", 90, False, gemini_client, state)

    assert state["status"] == "concluido"
    parecer = state["analysis"]["comentarios_analisados"]["parecer_comercial"]
    assert parecer["distribuicao_intencao_compra"]["alta"] == 0.5
    assert parecer["distribuicao_intencao_compra"]["media"] == 0.5
    assert parecer["faixa_etaria_predominante"] == "18-24"


def test_compute_eta_seconds_returns_none_when_mean_unknown():
    import app

    assert app._compute_eta_seconds(10, None) is None


def test_compute_eta_seconds_returns_none_when_nothing_remaining():
    import app

    assert app._compute_eta_seconds(0, 3.5) is None


def test_compute_eta_seconds_multiplies_remaining_by_mean():
    import app

    assert app._compute_eta_seconds(4, 3.5) == 14.0


def test_compute_eta_seconds_clamps_to_max_runtime_budget():
    import app

    assert app._compute_eta_seconds(1000, 3.5, max_runtime_budget=60.0) == 60.0


def test_format_eta_formats_seconds_only():
    import app

    assert app._format_eta(0) == "0s"
    assert app._format_eta(45) == "45s"


def test_format_eta_formats_minutes_and_seconds():
    import app

    assert app._format_eta(60) == "1min"
    assert app._format_eta(75) == "1min 15s"
    assert app._format_eta(125.6) == "2min 6s"


def test_make_coleta_progress_callback_updates_state_progressively():
    import app

    state = {}
    callback = app._make_coleta_progress_callback(state)

    callback(1, 4)
    assert state["etapa"] == "coleta"
    assert 0.05 <= state["progresso"] <= 0.30
    primeiro_progresso = state["progresso"]
    assert "1/4" in state["mensagem"]

    callback(2, 4)
    assert state["progresso"] > primeiro_progresso
    assert "2/4" in state["mensagem"]
    assert state["eta_seconds"] is not None
    assert state["eta_seconds"] >= 0


def test_run_pipeline_sets_pausado_seguranca_status_when_scrape_profile_raises_safe_stop(monkeypatch):
    import app
    from src import rate_controller, scraper

    def _raise_safe_stop(*args, **kwargs):
        raise rate_controller.SafeStop(reason="http_429")

    monkeypatch.setattr(scraper, "scrape_profile", _raise_safe_stop)

    state = {}
    app._run_pipeline("perfil_qualquer", 90, False, None, state)

    assert state["status"] == "pausado_seguranca"
    assert state["erro"] == rate_controller.SAFETY_MESSAGE
