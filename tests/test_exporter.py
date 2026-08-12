import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import exporter


def make_analysis(**overrides):
    base = {
        "username": "perfil_exemplo",
        "window_days": 90,
        "score_dodo": 7.35,
        "engagement_rate": 0.0421,
        "demografia": {
            "genero_predominante": "feminino",
            "regioes": ["SP", "RJ"],
        },
        "antifraude": {
            "pod_index": 0.12,
            "top_repetidores": {"user_a": 5, "user_b": 3},
            "taxa_resposta_criadora": 0.6,
        },
        "publis": [],
        "comentarios_analisados": {
            "total": 240,
            "qualificados": 58,
            "gemini_items": [
                {"comentario": "Quanto custa?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"},
            ],
        },
    }
    base.update(overrides)
    return base


def test_generate_html_report_is_self_contained_string():
    html = exporter.generate_html_report(make_analysis())

    assert isinstance(html, str)
    assert "<html" in html.lower()
    assert "<style" in html.lower()
    # sem CDN externo: nenhum link para folha de estilo remota
    assert "<link" not in html.lower()
    assert "cdn." not in html.lower()


def test_generate_html_report_contains_key_metrics():
    analysis = make_analysis()
    html = exporter.generate_html_report(analysis)

    assert "perfil_exemplo" in html
    assert "90" in html
    assert "7.35" in html or "7,35" in html
    assert "feminino" in html
    assert "SP" in html and "RJ" in html
    assert "0.12" in html or "12" in html  # pod_index
    assert "240" in html  # total de comentários
    assert "58" in html  # qualificados


def test_generate_html_report_marks_publis_as_placeholder_when_empty():
    html = exporter.generate_html_report(make_analysis(publis=[]))

    lowered = html.lower()
    assert "publi" in lowered
    # deve indicar explicitamente que não há dados de publis nesta rodada
    assert any(
        termo in lowered
        for termo in ("não implementado", "nao implementado", "placeholder", "em breve", "não disponível", "nao disponivel")
    )


def test_generate_html_report_shows_placeholder_when_no_regioes_detected():
    analysis = make_analysis()
    analysis["demografia"]["regioes"] = []
    html = exporter.generate_html_report(analysis)

    assert "não detectada" in html.lower() or "nao detectada" in html.lower() or "indeterminad" in html.lower()


def test_generate_html_report_escapes_username_to_avoid_html_injection():
    analysis = make_analysis(username="<script>alert(1)</script>")
    html = exporter.generate_html_report(analysis)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_generate_pdf_report_returns_valid_pdf_bytes():
    pdf_bytes = exporter.generate_pdf_report(make_analysis())

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")
    assert len(pdf_bytes) > 100


def test_generate_pdf_report_handles_empty_optional_collections():
    analysis = make_analysis()
    analysis["antifraude"]["top_repetidores"] = {}
    analysis["comentarios_analisados"]["gemini_items"] = []
    analysis["demografia"]["regioes"] = []

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")


def test_generate_pdf_report_handles_multiple_publis_items():
    """Mesma classe de regressão do teste de gemini_items, para o loop de publis
    (RF-09 ainda é placeholder em app.py, mas o exporter é genérico e aceita
    qualquer lista aqui)."""
    analysis = make_analysis()
    analysis["publis"] = [
        "Post patrocinado — Marca A — 12/07",
        "Post patrocinado — Marca B — 20/07",
        "Post patrocinado — Marca C — 02/08",
    ]

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")


def test_generate_pdf_report_handles_multiple_gemini_items():
    """Regressão: com 2+ itens do Gemini, cada `multi_cell` sem new_x/new_y
    explícitos deixava o cursor perto da margem direita, e o próximo multi_cell
    (largura automática até a margem) estourava com FPDFException
    'Not enough horizontal space to render a single character'."""
    analysis = make_analysis()
    analysis["comentarios_analisados"]["gemini_items"] = [
        {"comentario": "Qual o preço desse vestido?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"},
        {"comentario": "Vocês têm no tamanho M?", "intencao_compra": "media", "faixa_etaria_estimada": "18-24"},
        {"comentario": "Chega até Belo Horizonte?", "intencao_compra": "baixa", "faixa_etaria_estimada": "desconhecida"},
    ]

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")
