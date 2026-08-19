"""Testes de integração end-to-end da ISSUE-007 — fluxo completo simulado.

`src/app.py` é executado de ponta a ponta via `streamlit.testing.v1.AppTest`
(mesmo padrão já usado no histórico do projeto para homologar a View real).
Nenhum teste toca rede, banco real ou API do Gemini — `scraper.collect_profile`,
`database.get_cached_profile` e `ai_gemini.get_gemini_client` são sempre
mockados/injetados (SPEC issue-007 §2.3/§4).
"""

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.features.coleta import scraper
from src.features.relatorios import csv_exporter, pdf_exporter

_APP_PATH = str(Path(__file__).resolve().parents[1] / "src" / "app.py")

_FAKE_PROFILE_DATA = {"username": "criadora_teste", "bio": "bio de teste", "followers_count": 42000}
_FAKE_POSTS_DATA = [
    {
        "post_id": "p1", "format": "Foto", "published_at": "2026-06-01T00:00:00+00:00",
        "likes": 120, "comments_count": 8, "caption": "look novo", "is_sponsored": False,
    },
    {
        "post_id": "p2", "format": "Carrossel", "published_at": "2026-06-05T00:00:00+00:00",
        "likes": 200, "comments_count": 15, "caption": "#publi parceria", "is_sponsored": True,
    },
]
_FAKE_COMMENTS_DATA = [
    {"post_id": "p1", "username": "Ana Paula", "texto": "Amei o look!"},
    {"post_id": "p1", "username": "usuario123", "texto": "🔥🔥🔥"},
    {"post_id": "p2", "username": "Bruno Costa", "texto": "Onde compro, qual o preço?"},
]


def _fake_collect_profile(username, **kwargs):
    return {
        "status": "ok", "source": "real",
        "profile_data": _FAKE_PROFILE_DATA, "posts_data": _FAKE_POSTS_DATA, "comments_data": _FAKE_COMMENTS_DATA,
    }


def _run_audit_via_app(cached_profile=None, collect_side_effect=None):
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    with (
        patch("src.features.coleta.database.get_cached_profile", return_value=cached_profile),
        patch("src.features.coleta.scraper.collect_profile", side_effect=collect_side_effect or _fake_collect_profile),
        patch("src.features.analise.ai_gemini.get_gemini_client", return_value=None),
    ):
        at.run()
        at.text_input(key="input_username").set_value("@criadora_teste")
        at.button(key="btn_auditar_perfil").click()
        at.run()
    return at


# --- Fluxo completo com coleta real mockada -----------------------------------------------------------

def test_full_audit_flow_runs_without_exceptions():
    at = _run_audit_via_app()
    assert not at.exception


def test_full_audit_flow_populates_report_with_provenance():
    at = _run_audit_via_app()
    report = at.session_state["report"]
    assert report["status"] == "ok"
    assert report["perfil"]["username"] == "@criadora_teste"
    assert report["provenance"]["method_version"]
    assert report["provenance"]["window_days"] == 90
    assert report["provenance"]["posts_n"] == 2


def test_full_audit_flow_never_divides_by_zero_and_metricas_are_typed():
    at = _run_audit_via_app()
    report = at.session_state["report"]
    er = report["metricas"]["er_branding"]
    assert er is None or isinstance(er, (int, float))
    # BQI/CI seguem indisponíveis: dependem de save_rate/share_rate/VTR/alcance
    # qualificado (Pilar 2) e de séries semanais com piso aprovado (CI), que a
    # coleta pública via Instaloader não expõe (ISSUE-004 Rodadas 2/3).
    assert report["metricas"]["bqi"] is None
    assert report["metricas"]["ci"] is None
    # SD (saturação de publis) É real — calculável a partir de is_sponsored.
    assert isinstance(report["metricas"]["sd"], (int, float))


def test_full_audit_flow_aggregates_tipologia_and_formatos_from_real_pipeline():
    at = _run_audit_via_app()
    report = at.session_state["report"]
    assert set(report["tipologia"].keys()) == {"A", "B", "C", "D"}
    assert all(fmt["posts"] > 0 for fmt in report["formatos"])


def test_full_audit_flow_parecer_is_indisponivel_without_bqi_ci_sd():
    """Sem BQI/CI/SD resolvidos (Rodadas 2/3 bloqueadas), o parecer nunca
    fabrica um veredito — deve refletir a lacuna explicitamente."""
    at = _run_audit_via_app()
    report = at.session_state["report"]
    assert report["parecer_ia"]["status"] == "Indisponível"
    assert report["parecer_ia"]["ressalvas"]


# --- Modo cache -----------------------------------------------------------

def test_audit_flow_uses_cache_without_calling_scraper():
    cached = {
        "username": "criadora_teste", "profile_data": _FAKE_PROFILE_DATA,
        "posts_data": _FAKE_POSTS_DATA, "comments_data": _FAKE_COMMENTS_DATA,
        "created_at_utc": "2026-08-15T00:00:00+00:00", "ttl_seconds": 86400, "age_seconds": 10,
    }
    with patch("src.features.coleta.scraper.collect_profile") as mock_collect:
        at = _run_audit_via_app(cached_profile=cached)
        mock_collect.assert_not_called()
    report = at.session_state["report"]
    assert report["status_coleta"] == "Cache (24h)"


# --- Coleta indisponível (sem cache, sem rede) -----------------------------------------------------------

def test_audit_flow_shows_error_and_keeps_previous_report_when_collection_unavailable():
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    with (
        patch("src.features.coleta.database.get_cached_profile", return_value=None),
        patch("src.features.coleta.scraper.collect_profile", side_effect=scraper.ScraperError("rate_limit", 429)),
        patch("src.features.analise.ai_gemini.get_gemini_client", return_value=None),
    ):
        at.run()
        at.text_input(key="input_username").set_value("@perfil_sem_cache")
        at.button(key="btn_auditar_perfil").click()
        at.run()
    assert not at.exception
    assert at.session_state["report"]["perfil"]["username"] == "@perfilexemplo"  # MOCK_REPORT preservado
    assert any("Coleta indisponível" in str(e.value) for e in at.error)


# --- Sem posts no período (borda de divisão por zero) -----------------------------------------------------------

def test_audit_flow_handles_profile_with_no_posts_in_window():
    def _empty_posts_collect(username, **kwargs):
        return {
            "status": "ok", "source": "real",
            "profile_data": _FAKE_PROFILE_DATA, "posts_data": [], "comments_data": [],
        }

    at = _run_audit_via_app(collect_side_effect=_empty_posts_collect)
    assert not at.exception
    report = at.session_state["report"]
    assert report["formatos"] == []
    assert report["metricas"]["er_branding"] is None
    assert report["tipologia"] == {"A": 0, "B": 0, "C": 0, "D": 0}


# --- Exportação a partir de um payload real orquestrado -----------------------------------------------------------

def test_export_buttons_produce_bytes_from_real_orchestrated_payload():
    at = _run_audit_via_app()
    report = at.session_state["report"]
    pdf_bytes = pdf_exporter.generate_pdf_report(report)
    csv_bytes = csv_exporter.generate_csv_report(report)
    assert pdf_bytes.startswith(b"%PDF")
    assert csv_bytes.startswith(b"\xef\xbb\xbf")


# --- Modo Demonstração -----------------------------------------------------------

def _run_demo_via_app():
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    with patch("src.features.coleta.scraper.collect_profile") as mock_collect:
        at.run()
        at.button(key="btn_demo").click()
        at.run()
        mock_collect.assert_not_called()
    return at


def test_demo_flow_runs_without_exceptions_and_never_touches_scraper():
    at = _run_demo_via_app()
    assert not at.exception


def test_demo_flow_populates_dashboard_with_bqi_and_ci_available():
    """Diferente da auditoria real (BQI/CI sempre indisponíveis, ver acima),
    o Modo Demonstração simula os insumos do Pilar 2/CI para exercitar o
    dashboard 100% preenchido."""
    at = _run_demo_via_app()
    report = at.session_state["report"]
    assert report["status_coleta"] == "Modo demonstração (dados fictícios)"
    assert report["provenance"]["posts_n"] == 15
    metricas = report["metricas"]
    assert all(isinstance(metricas[chave], (int, float)) for chave in ("er_branding", "bqi", "ci", "sd"))
    assert sum(report["tipologia"].values()) > 0
    assert report["demografia"]["genero"]["coverage_pct"] > 0
    assert report["parecer_ia"]["status"] != "Indisponível"


def test_demo_flow_exports_produce_valid_bytes():
    at = _run_demo_via_app()
    report = at.session_state["report"]
    pdf_bytes = pdf_exporter.generate_pdf_report(report)
    csv_bytes = csv_exporter.generate_csv_report(report)
    assert pdf_bytes.startswith(b"%PDF")
    assert csv_bytes.startswith(b"\xef\xbb\xbf")
