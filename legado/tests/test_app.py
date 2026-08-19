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
    # botão de disparo do pipeline (SPRINT-003: renomeado de "Analisar" para
    # "Gerar relatório", pendência de nomenclatura da SPEC-002)
    button_labels = [b.label for b in at.button]
    assert any("Gerar relatório" in label for label in button_labels)


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
    # Sem clique em "Gerar relatório", não deve haver botões de download de relatório
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
    assert any("Posts de maior repercussão" in v for v in markdown_values)
    assert any("Posts com maior potencial de conversão" in v for v in markdown_values)

    campaign_insights = at.session_state["pipeline_state"]["analysis"]["campaign_insights"]
    assert campaign_insights is not None
    assert len(campaign_insights["top_3_by_quality"]) <= 3
    assert all(0.0 <= post["post_score"] <= 1.0 for post in campaign_insights["top_3_by_quality"])


def test_app_demo_mode_renders_content_affinity_cards(monkeypatch):
    """Sprint 002 SPEC-001 §6.6: os cards "Posts de maior repercussão"
    (ex-"Top 3 Posts"/"Top 3 por alcance/volume"), "Hashtags populares" e
    "Parcerias identificadas" (com menções de marcas, ex-"Menções de marcas")
    devem renderizar de fato na tela (via AppTest, não só chamada direta da
    função) ao final de um fluxo real de Modo Demonstração, já que
    demo_fetch_fn sempre gera posts patrocinados com hashtags e menções
    (i % 3 == 0, determinístico)."""
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

    markdown_values = [m.value for m in at.markdown]
    assert any("Posts de maior repercussão" in v for v in markdown_values)
    assert any("Hashtags populares" in v for v in markdown_values)
    assert any("Parcerias identificadas" in v for v in markdown_values)

    caption_values = " ".join(c.value for c in at.caption)
    assert "menç" in caption_values.lower()


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
    assert "Faixa etária predominante" in markdown_values
    assert "18-24" in markdown_values

    assert "sinal útil" in markdown_values.lower()


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


def test_app_hides_demo_pace_banner_in_demo_mode():
    """SPRINT-003 (/goal item 1, feedback transparente): em Modo Demonstração
    (sem rede real), o banner de ritmo seguro anti-bloqueio não deve
    aparecer — não há pacing real a explicar. (O caso positivo — banner
    visível durante coleta real — não é testável via AppTest: o runner só
    devolve o snapshot depois que a thread de pipeline em background já
    resolveu o status para fora de "rodando", então o estado transitório
    nunca fica observável na resposta de `.run()`; verificado manualmente
    no navegador via Playwright/execução real em vez de asserção
    automatizada.)"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_banner_demo_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    info_values = [i.value for i in at.info]
    assert not any("ritmo seguro anti-bloqueio" in value for value in info_values)


def test_app_hides_export_buttons_until_ver_relatorio_clicked():
    """SPEC-006 §2.4: as ações rápidas do header (Baixar PDF/Exportar CSV) não
    são gated por 'Ver Relatório' — só a seção 'Exportação' completa
    (HTML/PDF/JSON) no rodapé continua atrás desse gate, como antes."""
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
    quick_export_labels = sorted(b.label for b in at.download_button)
    assert quick_export_labels == ["Baixar PDF ↗", "Exportar CSV ↗"]
    ver_relatorio_button = next(b for b in at.button if b.label == "Ver Relatório")

    ver_relatorio_button.click().run()

    assert not at.exception
    # Ações rápidas do header (2) + seção "Exportação" completa liberada (3).
    assert len(at.download_button) == 5


def test_app_full_demo_flow_renders_title_sidebar_and_both_export_buttons(monkeypatch):
    """Sanity check de fechamento da Sprint 002 + SPRINT-003: título, sidebar
    de sessão do Instagram, badge de Modo Demonstração e os três botões de
    exportação (HTML, PDF e JSON — pendência da SPEC-002 fechada na
    SPRINT-003) devem aparecer sem exceção ao final do fluxo real Gerar
    relatório -> Ver Relatório."""
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
    assert any("HTML/PDF/JSON" in value for value in success_values)

    next(b for b in at.button if b.label == "Ver Relatório").click().run()

    assert not at.exception
    # SPEC-006 §2.4: além dos três da seção "Exportação" (HTML/PDF/JSON), o
    # header ganhou duas ações rápidas próprias (Baixar PDF/Exportar CSV).
    download_labels = sorted(b.label for b in at.download_button)
    assert download_labels == [
        "Baixar PDF ↗",
        "Baixar dados (JSON)",
        "Baixar relatório (HTML)",
        "Baixar relatório (PDF)",
        "Exportar CSV ↗",
    ]


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


# SPEC-005 / ISSUE-0010 (Sprint 004): mesmo motivo do bloco SPEC-004 abaixo —
# mantidos aqui, no bloco de testes AppTest.from_file, e não perto do fim do
# arquivo.


def test_full_demo_report_removes_score_dodo_from_top_and_keeps_it_legacy_in_audit(monkeypatch):
    """SPEC-005 §3.1/§8.2: 'Leitura para contratação' não pode mais existir
    como faixa de topo — o Score DODÔ só sobrevive, rotulado como legado, sob
    'Detalhes da auditoria'."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    at.text_input(key="username_input").set_value(f"perfil_sem_score_topo_{uuid.uuid4().hex}")
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
    subheader_values = [s.value for s in at.subheader]
    assert "Leitura para contratação" not in subheader_values

    markdown_values = [m.value for m in at.markdown]
    assert any("Score DODÔ (legado/derivado)" in value for value in markdown_values)


def test_full_demo_report_renders_three_comparable_format_cards(monkeypatch):
    """SPEC-005 §3.2/§4.3: Reels, Carrossel e Estático aparecem como cards
    comparáveis (demo_fetch_fn alterna os 3 formatos, então os três devem ter
    dados — nenhum em estado 'sem posts suficientes')."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    at.text_input(key="username_input").set_value(f"perfil_formatos_{uuid.uuid4().hex}")
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
    subheader_values = [s.value for s in at.subheader]
    assert "Formatos" in subheader_values

    markdown_values = [m.value for m in at.markdown]
    for label in ("**Reels**", "**Carrossel**", "**Estático**"):
        assert label in markdown_values

    caption_values = [c.value for c in at.caption]
    assert not any("Sem posts suficientes nesta janela." in value for value in caption_values)


def test_full_demo_report_renders_gender_bars_from_valid_sample_composition(monkeypatch):
    """SPEC-005 §4.1/§6.2: a demografia exibida usa a composição normalizada
    pela amostra válida (feminino_pct/masculino_pct), com cobertura amostral
    explícita — não o percentual bruto legado."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    at.text_input(key="username_input").set_value(f"perfil_demografia_ui_{uuid.uuid4().hex}")
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
    markdown_values = [m.value for m in at.markdown]
    assert any("Gênero (amostra válida e reconhecida):" in value for value in markdown_values)

    caption_values = [c.value for c in at.caption]
    assert any("Cobertura amostral de gênero:" in value for value in caption_values)


# SPEC-004: mantidos aqui, no bloco de testes AppTest.from_file, e não perto do
# fim do arquivo — testes que fazem `import app` bare (main() fora de
# ScriptRunContext) deixam lixo de estado de formulário que quebra
# AppTest.from_file() chamado depois (mesmo problema documentado em
# test_limpar_cache_button_clears_cached_profile_before_reanalyzing).


def test_inject_design_system_css_uses_white_button_text_and_spec004_card_border():
    """SPEC-004 §2.1/§4.2/checklist 9.2: botão primário tem texto #FFFFFF
    sobre #810100 — nunca o creme cannoli (#EDEBDD), que fica ilegível sobre
    o fundo vinho. A borda de card segue o token próprio da SPEC-004
    (#E5E0D8), não o cinza espuma (#E4D8CB) herdado do protótipo do portal."""
    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    css_markdown = " ".join(m.value for m in at.markdown if "stApp" in m.value)
    assert "color: #FFFFFF !important" in css_markdown
    assert "border: 1px solid #E5E0D8" in css_markdown
    # regressão: o bug de contraste da SPEC-004 usava a cor de fundo (creme
    # cannoli) como texto do botão — nunca deve voltar a aparecer ali.
    assert "color: #EDEBDD !important" not in css_markdown


def test_render_hashtags_populares_renders_pill_badges(monkeypatch):
    """SPEC-004 §3.2: hashtags aparecem como pílulas (classe `.dodo-badge`),
    não como tabela de duas colunas — demo_fetch_fn sempre gera hashtags
    orgânicas suficientes para passar o piso de relevância (ocorrências ≥ 2,
    POPULAR_TAGS_MIN_COUNT)."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    at.text_input(key="username_input").set_value(f"perfil_demo_hashtag_pill_{uuid.uuid4().hex}")
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

    markdown_values = [m.value for m in at.markdown]
    assert any("dodo-badge" in v for v in markdown_values)
    # a tabela antiga tinha cabeçalho "hashtag"/"ocorrências" — não deve mais existir
    dataframe_columns = [
        list(df.value.columns) if hasattr(df.value, "columns") else [] for df in at.dataframe
    ]
    assert not any({"hashtag", "ocorrências"}.issubset(set(cols)) for cols in dataframe_columns)


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
    Fase 4) está de fato ligado ao pipeline real.

    popular_tags é verificado com as tags orgânicas (#lookdodia/#moda, que
    aparecem em 3 dos 4 templates de legenda orgânica e portanto repetem de
    forma confiável entre os 4 posts orgânicos do demo) em vez de #publi/#ad
    — com só 2 posts patrocinados e 2 templates possíveis, exigir que os dois
    sorteiem o mesmo template para passar do piso de ruído
    (POPULAR_TAGS_MIN_COUNT, SPRINT-003) tornaria esta asserção instável."""
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
    assert any(tag["tag"] in {"#lookdodia", "#moda"} for tag in popular_tags["tags"])

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


def test_render_posts_maior_repercussao_never_raises_without_audit_report():
    import app

    app._render_posts_maior_repercussao({"username": "perfil_sem_audit_report"}, None)
    app._render_posts_maior_repercussao({"username": "perfil_audit_report_vazio", "audit_report": {}}, None)
    app._render_posts_maior_repercussao({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}}, None)


def test_render_hashtags_populares_never_raises_without_audit_report():
    import app

    app._render_hashtags_populares({"username": "perfil_sem_audit_report"})
    app._render_hashtags_populares({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}})


def test_render_parcerias_identificadas_never_raises_without_audit_report():
    import app

    app._render_parcerias_identificadas({"username": "perfil_sem_audit_report"})
    app._render_parcerias_identificadas({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}})


def test_render_audience_profile_never_raises_without_audit_report():
    import app

    analysis = {
        "username": "perfil_sem_audit_report",
        "demografia": {"genero_predominante": "indeterminado", "genero_pct": {}, "regioes": []},
    }
    app._render_audience_profile(analysis, False)
    app._render_audience_profile(analysis, True)


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
        def __init__(self, **kwargs):
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


# --- SPRINT-004 (SPEC-004): resumo limitado de parcerias (AppTest.from_function —
# nunca AppTest.from_file aqui: ver nota em test_limpar_cache_button_clears_cached_profile_before_reanalyzing
# sobre `import app` bare deixar lixo de estado de formulário para AppTest.from_file() seguintes).


def _script_render_parcerias_com_sete_itens(app_dir):
    import sys

    sys.path.insert(0, app_dir)
    import app

    publis = [
        {"post_id": f"sc_publi_{i}", "termos": ["#publi"], "marcas": [f"marca_{i}"]} for i in range(7)
    ]
    mentions = [
        {"handle": f"@marca_{i}", "count": i + 1, "tipo": "publi_confirmada" if i % 2 == 0 else "organica"}
        for i in range(7)
    ]
    analysis = {
        "username": "perfil_teste_parcerias",
        "publis": publis,
        "audit_report": {
            "metrics": {
                "brand_mentions": {"status": "ok", "mentions": mentions, "ressalvas": []},
            }
        },
    }
    app._render_parcerias_identificadas(analysis)


def test_render_parcerias_identificadas_resumo_caps_at_five_items():
    """SPEC-004 §3.2: 'A seção de parcerias mostra no máximo cinco itens no
    resumo' — com 7 publis e 7 menções, o resumo mostra só 5 de cada e avisa
    quantos itens adicionais ficam em Detalhes da auditoria."""
    import app

    app_dir = os.path.dirname(APP_PATH)
    at = AppTest.from_function(_script_render_parcerias_com_sete_itens, kwargs={"app_dir": app_dir})
    at.run()
    assert not at.exception

    caption_values = " ".join(c.value for c in at.caption)
    assert "+2 indício(s) adicional(is)" in caption_values
    assert "+2 menção(ões) adicional(is)" in caption_values

    dataframe_rows = [len(df.value) for df in at.dataframe if hasattr(df.value, "__len__")]
    assert all(rows <= app.PARCERIAS_RESUMO_MAX for rows in dataframe_rows)


def _script_render_audit_details_com_sete_parcerias(app_dir):
    import sys

    sys.path.insert(0, app_dir)
    import app

    publis = [
        {"post_id": f"sc_full_{i}", "termos": ["#publi"], "marcas": [f"marca_{i}"]} for i in range(7)
    ]
    mentions = [{"handle": f"@marca_{i}", "count": i + 1, "tipo": "publi_confirmada"} for i in range(7)]
    analysis = {
        "average_likes": 0.0,
        "average_comments": 0.0,
        "antifraude": {},
        "comentarios_analisados": {},
        "audit_report": {
            "metrics": {"brand_mentions": {"status": "ok", "mentions": mentions, "ressalvas": []}},
        },
        "publis": publis,
    }
    app._render_audit_details(analysis, {})


def test_render_audit_details_contains_full_parcerias_inventory():
    """SPEC-004 §3.2: o inventário completo (sem corte de 5 itens) fica em
    Detalhes da auditoria, nunca fora da tela por completo."""
    app_dir = os.path.dirname(APP_PATH)
    at = AppTest.from_function(_script_render_audit_details_com_sete_parcerias, kwargs={"app_dir": app_dir})
    at.run()
    assert not at.exception

    dataframe_rows = [len(df.value) for df in at.dataframe if hasattr(df.value, "__len__")]
    assert any(rows == 7 for rows in dataframe_rows)


def test_render_format_performance_never_raises_without_audit_report():
    import app

    app._render_format_performance({"username": "perfil_sem_audit_report"})
    app._render_format_performance({"username": "perfil_metrics_vazio", "audit_report": {"metrics": {}}})


# SPEC-006: estados de fluxo, ações rápidas e mini-cards de parceria.


def test_progress_stage_mapping_covers_every_pipeline_step():
    """SPEC-006 §2.1: o indicador de 3 estágios precisa mapear TODAS as
    etapas internas de PIPELINE_STEPS — uma etapa nova adicionada ao pipeline
    sem entrada correspondente aqui ficaria muda no indicador (cairia no
    default do .get(), sempre estágio 1, silenciosamente errado)."""
    import app

    assert set(app._PROGRESS_STAGE_BY_ETAPA) == set(app.PIPELINE_STEPS)
    assert app._PROGRESS_STAGE_BY_ETAPA["coleta"] == 0
    assert app._PROGRESS_STAGE_BY_ETAPA["relatorio"] == 2


def test_render_progress_stage_indicator_never_raises_for_known_and_unknown_etapas():
    import app

    for etapa in list(app.PIPELINE_STEPS) + ["etapa_desconhecida"]:
        app._render_progress_stage_indicator(etapa)


def test_hero_entrada_shown_only_while_idle():
    """SPEC-006 §1.1 item 1: a moldura editorial só aparece antes de qualquer
    tentativa de análise — some assim que o pipeline conclui."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    idle_markdown_values = [m.value for m in at.markdown]
    assert any("Audite qualquer perfil do Instagram" in v for v in idle_markdown_values)

    at.text_input(key="username_input").set_value(f"perfil_hero_{uuid.uuid4().hex}")
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
    concluido_markdown_values = [m.value for m in at.markdown]
    assert not any("Audite qualquer perfil do Instagram" in v for v in concluido_markdown_values)


def test_reanalisar_perfil_button_resets_screen_without_clearing_cache(monkeypatch):
    """SPEC-006 §1.1 item 6: o botão discreto dentro de 'Detalhes da
    auditoria' faz o mesmo reset de tela que 'Gerar novo relatório' — nunca
    limpa o cache, só o estado da tela (mesma garantia já testada para o
    botão homônimo do rodapé)."""
    from src import database

    clear_cache_calls = []
    monkeypatch.setattr(database, "clear_profile_cache", lambda username: clear_cache_calls.append(username))

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_reanalisar_{uuid.uuid4().hex}")
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
    next(b for b in at.button if b.label == "↻ Reanalisar perfil").click().run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "ocioso"
    assert at.session_state["mostrar_relatorio"] is False
    assert clear_cache_calls == []


def test_parceria_mini_card_renders_avatar_and_real_post_link():
    """SPEC-006 §2.3: cada parceria detectada em Modo Demonstração (legendas
    de exemplo com @marca_fashion_demo/@outra_marca_demo/@marca_parceira)
    deve virar um mini-card com avatar circular de iniciais e o link real
    daquele post — não um Retângulo neutro nem um href inventado."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_parceria_{uuid.uuid4().hex}")
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
    markdown_html = "\n".join(m.value for m in at.markdown)
    assert 'class="dodo-avatar-circle"' in markdown_html
    assert 'class="dodo-pill-link"' in markdown_html
    assert "instagram.com/p/" in markdown_html
