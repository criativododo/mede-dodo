"""Testes unitários da ISSUE-006 — exportadores de relatório (PDF e CSV).

Os exportadores são puros: recebem um dicionário já resolvido (o mesmo shape
de `st.session_state.report` em `src/app.py`) e nunca recalculam métricas,
acessam rede/disco ou fabricam valores ausentes (princípio "zero silencioso").
"""

import csv
import io

from src.features.relatorios import csv_exporter, pdf_exporter

# --- payload de referência (mesmo shape do MOCK_REPORT em src/app.py) -----------------

FULL_PAYLOAD = {
    "perfil": {
        "username": "@perfilexemplo",
        "marca_contratante": "Jescri Lingerie",
        "porte": "Micro",
        "seguidores": 42800,
    },
    "janela": {"dias": 90, "rotulo": "Janela trimestral (90 dias)"},
    "metricas": {"er_branding": 4.8, "bqi": 82, "ci": 78, "sd": 18},
    "formatos": [
        {"formato": "Reels", "posts": 14, "er": 5.6},
        {"formato": "Carrossel", "posts": 9, "er": 4.1},
    ],
    "tipologia": {"A": 20, "B": 32, "C": 21, "D": 27},
    "demografia": {
        "genero": {"female_pct": 62.0, "male_pct": 30.0, "unknown_pct": 8.0, "coverage_pct": 92.0},
        "localizacao": {"top_estados": [{"uf": "SP", "mencoes": 12}], "coverage_pct": 40.0},
    },
    "parecer_ia": {
        "status": "Recomendada com Alta Afinidade",
        "pontos_fortes": ["Consistência editorial acima do saudável (CI 78%)"],
        "bloqueadores": [],
        "ressalvas": ["Amostra de comentários ainda não coletada nesta sessão."],
    },
    "provenance": {
        "method_version": "BMQ-001-v2.0.0-r1",
        "window_days": 90,
        "posts_n": 2,
        "generated_at_utc": "2026-08-15T12:00:00Z",
    },
    "posts": [
        {
            "post_id": "p1",
            "format": "foto",
            "published_at": "2026-06-01",
            "likes": 100,
            "comments": 5,
            "shares": 2,
            "saves": 3,
            "reach": 1000,
            "is_sponsored": False,
        },
    ],
}

MINIMAL_PAYLOAD = {
    "perfil": {"username": "@minimo"},
    "janela": {"dias": 90, "rotulo": "Janela trimestral (90 dias)"},
    "metricas": {"er_branding": 4.8},
}

# --- csv_exporter -----------------------------------------------------------

def test_generate_csv_report_returns_utf8_sig_bytes():
    result = csv_exporter.generate_csv_report(FULL_PAYLOAD)
    assert isinstance(result, bytes)
    assert result.startswith(b"\xef\xbb\xbf")


def test_generate_csv_report_includes_profile_metadata():
    text = csv_exporter.generate_csv_report(FULL_PAYLOAD).decode("utf-8-sig")
    assert "@perfilexemplo" in text
    assert "Jescri Lingerie" in text
    assert "BMQ-001-v2.0.0-r1" in text


def test_generate_csv_report_includes_consolidated_metrics():
    text = csv_exporter.generate_csv_report(FULL_PAYLOAD).decode("utf-8-sig")
    assert "4.8" in text
    assert "82" in text
    assert "78" in text
    assert "18" in text


def test_generate_csv_report_includes_posts_table_with_rows():
    text = csv_exporter.generate_csv_report(FULL_PAYLOAD).decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    flat = [cell for row in rows for cell in row]
    assert "post_id" in flat
    assert "p1" in flat
    assert "1000" in flat


def test_generate_csv_report_missing_posts_never_fabricates_rows():
    text = csv_exporter.generate_csv_report(MINIMAL_PAYLOAD).decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    header_idx = next(i for i, row in enumerate(rows) if row and row[0] == "post_id")
    assert len(rows) == header_idx + 1


def test_generate_csv_report_missing_optional_metric_shows_explicit_placeholder():
    text = csv_exporter.generate_csv_report(MINIMAL_PAYLOAD).decode("utf-8-sig")
    assert "indisponivel" in text or "indisponível" in text


def test_generate_csv_report_is_deterministic_for_the_same_payload():
    first = csv_exporter.generate_csv_report(FULL_PAYLOAD)
    second = csv_exporter.generate_csv_report(FULL_PAYLOAD)
    assert first == second


# --- pdf_exporter -----------------------------------------------------------

def test_generate_pdf_report_returns_valid_pdf_bytes():
    result = pdf_exporter.generate_pdf_report(FULL_PAYLOAD)
    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")
    assert len(result) > 500


def test_generate_pdf_report_includes_profile_and_metrics_text():
    result = pdf_exporter.generate_pdf_report(FULL_PAYLOAD)
    assert b"perfilexemplo" in result
    assert b"Jescri Lingerie" in result


def test_generate_pdf_report_includes_provenance_footer():
    result = pdf_exporter.generate_pdf_report(FULL_PAYLOAD)
    assert b"BMQ-001-v2.0.0-r1" in result


def test_generate_pdf_report_handles_missing_optional_blocks_without_crashing():
    result = pdf_exporter.generate_pdf_report(MINIMAL_PAYLOAD)
    assert result.startswith(b"%PDF")
    assert len(result) > 500


def test_generate_pdf_report_missing_metric_never_shows_silent_zero():
    result = pdf_exporter.generate_pdf_report(MINIMAL_PAYLOAD)
    text = result.decode("latin-1")
    assert "indisponivel" in text or "indisponível" in text.encode("latin-1").decode("latin-1") or "indispon" in text


def test_generate_pdf_report_is_deterministic_for_the_same_payload():
    first = pdf_exporter.generate_pdf_report(FULL_PAYLOAD)
    second = pdf_exporter.generate_pdf_report(FULL_PAYLOAD)
    assert first == second


def test_generate_pdf_report_never_crashes_on_typographic_punctuation():
    """Regressão: a fonte core `helvetica` do fpdf2 é latin-1 — texto do
    parecer com travessão/aspas curvas (comum no parecer local gerado por
    `ai_local.build_local_opinion`) derrubava `generate_pdf_report` com
    `FPDFUnicodeEncodingException` assim que BQI/CI/SD ficavam resolvidos
    (só passou a acontecer de verdade com o Modo Demonstração — em
    auditorias reais BQI/CI sempre ficam `indisponivel`)."""
    payload = dict(FULL_PAYLOAD)
    payload["parecer_ia"] = {
        "status": "Recomendada com Ressalvas",
        "pontos_fortes": ["BQI de 70.3/100 (saudável) — acima da média do nicho"],
        "bloqueadores": [],
        "ressalvas": [
            "Parecer gerado localmente (Gemini indisponível ou não configurado) — "
            "recomenda-se revisão humana.",
            "V_AB ≥ 40% — patamar saudável “confirmado”…",
        ],
    }
    result = pdf_exporter.generate_pdf_report(payload)
    assert result.startswith(b"%PDF")
    assert len(result) > 500
