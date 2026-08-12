import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


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


def test_app_demo_pipeline_runs_end_to_end_without_gemini_api_key(monkeypatch):
    """Sem GEMINI_API_KEY no ambiente, o Modo Demonstração continua funcionando
    fim-a-fim: RealGeminiClient() levanta RuntimeError, app.py deve capturar isso
    e seguir com gemini_client=None, sem exceção não tratada."""
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
    assert at.session_state["pipeline_state"]["gemini_configurado"] is False


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
    assert "erro" in state
