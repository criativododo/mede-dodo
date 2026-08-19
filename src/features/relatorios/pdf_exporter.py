"""Exportador PDF editorial (ISSUE-006) — Dossiê métricaDODÔ via fpdf2.

100% Python puro, sem rede/banco/disco/Streamlit (SPEC-001 §3.5, DUMMY.md §4).
Recebe o payload já resolvido (mesmo shape de `st.session_state.report` em
`src/app.py`) e nunca recalcula métricas nem fabrica valores ausentes — campos
sem dado disponível são explicitados como "indisponível", nunca omitidos ou
zerados silenciosamente. Compressão desligada deliberadamente: mantém o PDF
determinístico byte-a-byte para o mesmo payload (governança §5 da ISSUE-006).
"""

from fpdf import FPDF

_CANNOLI = (245, 244, 236)
_VERMELHO_HAUTE = (129, 1, 0)
_BORDA = (229, 224, 216)
_TEXTO_PRINCIPAL = (26, 26, 26)
_TEXTO_SECUNDARIO = (100, 100, 100)

_PLACEHOLDER = "indisponível"

# fpdf2 usa a fonte core "helvetica" (charset latin-1) por padrão — texto
# editorial em PT-BR (parecer da IA, warnings) usa pontuação tipográfica fora
# desse charset (travessão, aspas curvas), que antes nunca chegava ao PDF
# porque BQI/CI/SD ficavam sempre `indisponivel` em auditorias reais. Com o
# Modo Demonstração (BQI/CI/SD resolvidos), o texto do parecer local
# (`ai_local.build_local_opinion`) alcança esse caminho e quebra o fpdf2 com
# `FPDFUnicodeEncodingException`. Transliteração determinística para
# ASCII/latin-1 em vez de trocar a fonte — mantém o PDF determinístico
# byte-a-byte para o mesmo payload (governança §5 da ISSUE-006) sem depender
# de um arquivo de fonte Unicode externo.
_LATIN1_TRANSLITERATIONS = {
    "—": "-",  # — em dash
    "–": "-",  # – en dash
    "‘": "'",  # '
    "’": "'",  # '
    "“": '"',  # "
    "”": '"',  # "
    "…": "...",  # …
    "≥": ">=",  # ≥
    "≤": "<=",  # ≤
}


def _safe_text(text: str) -> str:
    if not text:
        return text
    for original, substituto in _LATIN1_TRANSLITERATIONS.items():
        text = text.replace(original, substituto)
    return text


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return _PLACEHOLDER
    return _safe_text(f"{value}{suffix}")


def _new_pdf() -> FPDF:
    pdf = FPDF(orientation="P", format="A4")
    pdf.set_compression(False)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_fill_color(*_CANNOLI)
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")
    return pdf


def _draw_header(pdf: FPDF, perfil: dict, janela: dict) -> None:
    pdf.set_text_color(*_VERMELHO_HAUTE)
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, "métricaDODÔ - Dossiê Editorial de Influência", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(*_TEXTO_PRINCIPAL)
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 7, _fmt(perfil.get("username")), new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(*_TEXTO_SECUNDARIO)
    pdf.set_font("helvetica", "", 9)
    pdf.cell(0, 6, f"Marca contratante: {_fmt(perfil.get('marca_contratante'))}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Janela: {_fmt(janela.get('rotulo'))}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_draw_color(*_BORDA)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(5)


def _draw_metric_cards(pdf: FPDF, metricas: dict) -> None:
    cards = [
        ("ER Branding", _fmt(metricas.get("er_branding"), "%")),
        ("BQI", _fmt(metricas.get("bqi"), "/100")),
        ("Consistência (CI)", _fmt(metricas.get("ci"), "%")),
        ("Saturação (SD)", _fmt(metricas.get("sd"), "%")),
    ]
    card_width = (pdf.w - pdf.l_margin - pdf.r_margin - 3 * 4) / 4
    y_start = pdf.get_y()
    for index, (label, value) in enumerate(cards):
        x = pdf.l_margin + index * (card_width + 4)
        pdf.set_xy(x, y_start)
        pdf.set_draw_color(*_BORDA)
        pdf.rect(x, y_start, card_width, 20)
        pdf.set_xy(x + 2, y_start + 3)
        pdf.set_text_color(*_TEXTO_SECUNDARIO)
        pdf.set_font("helvetica", "", 8)
        pdf.cell(card_width - 4, 5, label)
        pdf.set_xy(x + 2, y_start + 10)
        pdf.set_text_color(*_VERMELHO_HAUTE)
        pdf.set_font("helvetica", "B", 13)
        pdf.cell(card_width - 4, 7, value)
    pdf.set_xy(pdf.l_margin, y_start + 24)


def _draw_section_title(pdf: FPDF, title: str) -> None:
    pdf.set_text_color(*_TEXTO_PRINCIPAL)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")


def _draw_distribuicoes(pdf: FPDF, formatos: list, tipologia: dict, demografia: dict) -> None:
    _draw_section_title(pdf, "Distribuições & Demografia")
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*_TEXTO_PRINCIPAL)

    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "Formatos", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    if formatos:
        for linha in formatos:
            pdf.cell(
                0, 5,
                _safe_text(
                    f"{linha.get('formato', _PLACEHOLDER)}: {linha.get('posts', _PLACEHOLDER)} posts "
                    f"· ER {_fmt(linha.get('er'), '%')}"
                ),
                new_x="LMARGIN", new_y="NEXT",
            )
    else:
        pdf.cell(0, 5, _PLACEHOLDER, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "Tipologia de comentários (A/B/C/D)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    if tipologia:
        linha_tipologia = " · ".join(f"{chave}: {_fmt(valor, '%')}" for chave, valor in tipologia.items())
        pdf.cell(0, 5, _safe_text(linha_tipologia), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 5, _PLACEHOLDER, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    genero = (demografia or {}).get("genero") or {}
    localizacao = (demografia or {}).get("localizacao") or {}
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "Gênero estimado / Top estados por DDD", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    pdf.cell(
        0, 5,
        f"Feminino: {_fmt(genero.get('female_pct'), '%')} · Masculino: {_fmt(genero.get('male_pct'), '%')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    top_estados = localizacao.get("top_estados") or []
    if top_estados:
        estados_txt = " · ".join(f"{e.get('uf')}: {e.get('mencoes')}" for e in top_estados)
    else:
        estados_txt = _PLACEHOLDER
    pdf.cell(0, 5, _safe_text(estados_txt), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _draw_parecer(pdf: FPDF, parecer: dict) -> None:
    _draw_section_title(pdf, "Parecer Editorial")
    x, y = pdf.l_margin, pdf.get_y()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_draw_color(*_VERMELHO_HAUTE)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(*_VERMELHO_HAUTE)
    pdf.cell(0, 7, _fmt(parecer.get("status")), new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(*_TEXTO_PRINCIPAL)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "Pontos fortes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    pontos_fortes = parecer.get("pontos_fortes") or []
    if pontos_fortes:
        for ponto in pontos_fortes:
            pdf.multi_cell(width, 5, _safe_text(f"- {ponto}"))
            pdf.set_x(pdf.l_margin)
    else:
        pdf.cell(0, 5, _PLACEHOLDER, new_x="LMARGIN", new_y="NEXT")

    ressalvas = parecer.get("ressalvas") or []
    if ressalvas:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(0, 6, "Ressalvas para o briefing", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 9)
        for ressalva in ressalvas:
            pdf.multi_cell(width, 5, _safe_text(f"- {ressalva}"))
            pdf.set_x(pdf.l_margin)

    height = pdf.get_y() - y
    pdf.set_draw_color(*_VERMELHO_HAUTE)
    pdf.rect(x, y, width, max(height, 10))
    pdf.ln(3)


def _draw_footer(pdf: FPDF, provenance: dict) -> None:
    pdf.set_draw_color(*_BORDA)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(*_TEXTO_SECUNDARIO)
    pdf.set_font("helvetica", "", 7)
    carimbo = (
        f"Método: {_fmt(provenance.get('method_version'))} · "
        f"Janela: {_fmt(provenance.get('window_days'), ' dias')} · "
        f"Posts analisados: {_fmt(provenance.get('posts_n'))} · "
        f"Gerado em (UTC): {_fmt(provenance.get('generated_at_utc'))}"
    )
    pdf.multi_cell(0, 4, carimbo)


def generate_pdf_report(data: dict) -> bytes:
    """Compõe o dossiê editorial A4 (Header, Cards de Métricas,
    Distribuições/Demografia, Parecer Editorial e Rodapé de Proveniência) e
    retorna `bytes(pdf.output())`."""
    perfil = data.get("perfil") or {}
    janela = data.get("janela") or {}
    metricas = data.get("metricas") or {}
    formatos = data.get("formatos") or []
    tipologia = data.get("tipologia") or {}
    demografia = data.get("demografia") or {}
    parecer = data.get("parecer_ia") or {}
    provenance = data.get("provenance") or {}

    pdf = _new_pdf()
    _draw_header(pdf, perfil, janela)
    _draw_metric_cards(pdf, metricas)
    pdf.ln(5)
    _draw_distribuicoes(pdf, formatos, tipologia, demografia)
    _draw_parecer(pdf, parecer)
    _draw_footer(pdf, provenance)

    return bytes(pdf.output())
