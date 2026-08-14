import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import exporter, metrics


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


def test_generate_html_report_shows_genuine_empty_state_when_no_publis_detected():
    html = exporter.generate_html_report(make_analysis(publis=[]))

    lowered = html.lower()
    assert "publi" in lowered
    # RF-09 é real agora: não pode mais dizer que a funcionalidade não foi implementada
    assert "não implementado" not in lowered and "nao implementado" not in lowered
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


def test_generate_html_report_shows_parecer_comercial_when_present():
    analysis = make_analysis()
    analysis["comentarios_analisados"]["parecer_comercial"] = {
        "indicador": "alto",
        "pct_interesse_comercial": 0.6,
        "pct_validacao_pessoal": 0.2,
        "pct_duvida_critica": 0.1,
        "pct_spam_ruido": 0.1,
        "comentarios_alta_intencao": 2,
        "alertas": ["Índice de pods elevado (35%) — parte do engajamento pode ser coordenado/artificial."],
        "resumo": "2 comentário(s) com intenção de compra alta.",
    }

    html = exporter.generate_html_report(analysis)

    assert "brand suitability" in html.lower()
    assert "Alto potencial de conversão" in html
    assert "Índice de pods elevado" in html


def test_generate_html_report_omits_parecer_comercial_when_absent():
    html = exporter.generate_html_report(make_analysis())

    assert "brand suitability" not in html.lower()


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
    """Mesma classe de regressão do teste de gemini_items, para o loop de
    publis — agora com o formato real produzido por detect_sponsored_posts
    (RF-09)."""
    analysis = make_analysis()
    analysis["publis"] = [
        {"post_id": "1", "shortcode": "a1", "link": "https://www.instagram.com/p/a1/", "termos": ["#publi"], "marcas": ["marca_a"]},
        {"post_id": "2", "shortcode": "a2", "link": "https://www.instagram.com/p/a2/", "termos": ["parceria"], "marcas": ["marca_b"]},
        {"post_id": "3", "shortcode": "a3", "link": "https://www.instagram.com/p/a3/", "termos": ["patrocinado"], "marcas": ["marca_c"]},
    ]

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")


def test_generate_pdf_report_handles_parecer_comercial_with_multiple_alertas():
    """Mesma classe de regressão dos outros loops de PDF: parecer_comercial com
    2+ alertas e itens do Gemini com categoria_sentimento/sinais_compra não
    pode estourar FPDFException por multi_cell sem new_x/new_y explícitos."""
    analysis = make_analysis()
    analysis["comentarios_analisados"]["gemini_items"] = [
        {
            "comentario": "Qual o preço desse vestido?",
            "intencao_compra": "alta",
            "faixa_etaria_estimada": "25-34",
            "categoria_sentimento": "interesse_comercial",
            "sinais_compra": ["preco", "onde_comprar"],
        },
        {
            "comentario": "Vocês têm no tamanho M?",
            "intencao_compra": "media",
            "faixa_etaria_estimada": "18-24",
            "categoria_sentimento": "interesse_comercial",
            "sinais_compra": ["tamanho"],
        },
    ]
    analysis["comentarios_analisados"]["parecer_comercial"] = {
        "indicador": "baixo",
        "pct_interesse_comercial": 0.2,
        "pct_validacao_pessoal": 0.1,
        "pct_duvida_critica": 0.1,
        "pct_spam_ruido": 0.6,
        "comentarios_alta_intencao": 1,
        "alertas": [
            "Índice de pods elevado (42%) — parte do engajamento pode ser coordenado/artificial.",
            "60% dos comentários qualificados ainda são ruído/spam mesmo após o filtro local.",
        ],
        "resumo": "1 comentário(s) com intenção de compra alta.",
    }

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


# --- Proveniência e Escopo das Métricas (Sprint 002 Fase 2, ETAPA 3.3) ---


def _make_audit_report_with_followers_only():
    posts = [{"likes_count": 100, "comments_count": 10}]
    return metrics.build_audit_report(posts, followers_count=1000)


def test_generate_html_report_includes_provenance_section_with_available_and_unavailable_metrics():
    analysis = make_analysis(audit_report=_make_audit_report_with_followers_only())

    html = exporter.generate_html_report(analysis)

    assert "Proveniência e Escopo das Métricas" in html
    assert "Por seguidores" in html
    assert "Disponível" in html
    assert "Por alcance" in html
    assert "Por views de Reels" in html
    assert "Indisponível nesta amostra" in html
    assert "local_scraper_sample" in html


def test_generate_html_report_handles_missing_audit_report_gracefully():
    analysis = make_analysis()  # sem "audit_report" — mesmo formato de analyses pré-Sprint 002 Fase 2
    assert "audit_report" not in analysis

    html = exporter.generate_html_report(analysis)

    assert "Proveniência e Escopo das Métricas" in html
    assert "ainda não disponível" in html


def test_generate_pdf_report_includes_provenance_section_without_raising():
    analysis = make_analysis(audit_report=_make_audit_report_with_followers_only())

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")


def test_generate_pdf_report_handles_missing_audit_report_gracefully():
    analysis = make_analysis()

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")


# --- Sprint 002 Fase 4: Top Posts / Hashtags populares / Menções de marcas -


def _make_audit_report_with_content_affinity():
    posts = [
        {
            "post_id": "1",
            "likes_count": 500,
            "comments_count": 50,
            "raw": {
                "shortcode": "aaa",
                "caption": "look novo #moda #verao com @marca_publi, publi paga #publi",
                "published_at": "2026-08-01T00:00:00+00:00",
                "media_type": "REEL",
                "comments": [],
            },
        },
        {
            "post_id": "2",
            "likes_count": 100,
            "comments_count": 10,
            "raw": {
                "shortcode": "bbb",
                "caption": "amei essa peça #moda, adorei @marca_organica",
                "published_at": "2026-08-02T00:00:00+00:00",
                "media_type": "IMAGE",
                "comments": [],
            },
        },
    ]
    return metrics.build_audit_report(posts, followers_count=1000)


def test_generate_html_report_includes_top_posts_hashtags_and_mentions_when_available():
    analysis = make_analysis(audit_report=_make_audit_report_with_content_affinity())

    html = exporter.generate_html_report(analysis)

    assert "Top 3 Posts" in html
    assert "https://www.instagram.com/p/aaa/" in html
    assert "Hashtags populares" in html
    assert "#moda" in html
    assert "Menções de marcas" in html
    assert "@marca_publi" in html and "@marca_organica" in html
    assert "publi confirmada" in html
    assert "menção orgânica" in html


def test_generate_html_report_shows_placeholders_when_content_affinity_unavailable():
    analysis = make_analysis(audit_report=_make_audit_report_with_followers_only())

    html = exporter.generate_html_report(analysis)

    assert exporter.POPULAR_TAGS_VAZIO_MSG in html
    assert exporter.BRAND_MENTIONS_VAZIO_MSG in html


def test_generate_html_report_shows_demographic_coverage_when_available():
    posts = [
        {
            "post_id": "1",
            "raw": {
                "comments": [
                    {"username": "maria_silva", "texto": "moro em sao paulo"},
                    {"username": "joao_pedro", "texto": "top"},
                ]
            },
        }
    ]
    audit_report = metrics.build_audit_report(posts, followers_count=1000)
    analysis = make_analysis(audit_report=audit_report)

    html = exporter.generate_html_report(analysis)

    assert "Cobertura de gênero identificado" in html
    assert "Cobertura de região identificada" in html
    assert "amostragem de comentários públicos" in html


def test_generate_pdf_report_includes_content_affinity_sections_without_raising():
    analysis = make_analysis(audit_report=_make_audit_report_with_content_affinity())

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")


def test_generate_pdf_report_handles_content_affinity_unavailable_gracefully():
    analysis = make_analysis(audit_report=_make_audit_report_with_followers_only())

    pdf_bytes = exporter.generate_pdf_report(analysis)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")
