"""Exportação do relatório de auditoria de perfil (HTML autocontido e PDF via fpdf2).

Funções puras: recebem o dicionário `analysis` (formato canônico descrito em
docs/issues/ISSUE-0004.md) e devolvem o relatório pronto para download, sem
tocar em disco, rede ou `st.session_state` — isso fica a cargo de `app.py`.
"""

import html as html_lib

from fpdf import FPDF

PUBLIS_PLACEHOLDER_MSG = (
    "Varredura de publis (RF-09) não implementada nesta rodada — placeholder "
    "reservado para issue futura."
)
GEMINI_NAO_CONFIGURADO_MSG = "Análise de intenção via Gemini não configurada nesta sessão."


def _fmt_pct(value):
    try:
        return f"{value * 100:.2f}%"
    except (TypeError, ValueError):
        return "N/D"


def _fmt_float(value, casas=2):
    try:
        return f"{value:.{casas}f}"
    except (TypeError, ValueError):
        return "N/D"


def _regioes_texto(regioes):
    if not regioes:
        return "Nenhuma região detectada (indeterminado)"
    return ", ".join(regioes)


def _pdf_safe(text):
    """fpdf2 com fonte core (helvetica) só suporta latin-1: normaliza pontuação
    tipográfica comum (travessão, aspas curvas, reticências) e descarta o resto
    com segurança em vez de lançar FPDFUnicodeEncodingException."""
    text = str(text)
    replacements = {
        "—": "-",
        "–": "-",
        "…": "...",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
    }
    for original, substituto in replacements.items():
        text = text.replace(original, substituto)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _top_repetidores_linhas(top_repetidores):
    if not top_repetidores:
        return []
    return sorted(top_repetidores.items(), key=lambda item: item[1], reverse=True)


def generate_html_report(analysis: dict) -> str:
    """Gera um relatório HTML autocontido (CSS inline, sem CDN externo)."""

    username = html_lib.escape(str(analysis.get("username", "")))
    window_days = analysis.get("window_days", "N/D")
    score = _fmt_float(analysis.get("score_dodo"))
    engagement = _fmt_pct(analysis.get("engagement_rate"))

    demografia = analysis.get("demografia", {}) or {}
    genero = html_lib.escape(str(demografia.get("genero_predominante", "indeterminado")))
    regioes_texto = html_lib.escape(_regioes_texto(demografia.get("regioes")))

    antifraude = analysis.get("antifraude", {}) or {}
    pod_index = _fmt_float(antifraude.get("pod_index"))
    taxa_resposta = _fmt_pct(antifraude.get("taxa_resposta_criadora"))
    top_repetidores = _top_repetidores_linhas(antifraude.get("top_repetidores"))
    if top_repetidores:
        top_repetidores_html = "".join(
            f"<li>{html_lib.escape(str(user))}: {html_lib.escape(str(count))} comentários</li>"
            for user, count in top_repetidores
        )
    else:
        top_repetidores_html = "<li>Nenhum repetidor relevante identificado</li>"

    publis = analysis.get("publis", []) or []
    if publis:
        publis_html = "".join(f"<li>{html_lib.escape(str(item))}</li>" for item in publis)
    else:
        publis_html = f"<p class='placeholder'>{html_lib.escape(PUBLIS_PLACEHOLDER_MSG)}</p>"

    comentarios = analysis.get("comentarios_analisados", {}) or {}
    total_comentarios = comentarios.get("total", 0)
    qualificados = comentarios.get("qualificados", 0)
    gemini_items = comentarios.get("gemini_items", []) or []
    if gemini_items:
        gemini_html = "".join(
            "<tr>"
            f"<td>{html_lib.escape(str(item.get('comentario', '')))}</td>"
            f"<td>{html_lib.escape(str(item.get('intencao_compra', '')))}</td>"
            f"<td>{html_lib.escape(str(item.get('faixa_etaria_estimada', '')))}</td>"
            "</tr>"
            for item in gemini_items
        )
        gemini_section = f"""
        <table>
            <thead><tr><th>Comentário</th><th>Intenção de compra</th><th>Faixa etária estimada</th></tr></thead>
            <tbody>{gemini_html}</tbody>
        </table>
        """
    else:
        gemini_section = f"<p class='placeholder'>{html_lib.escape(GEMINI_NAO_CONFIGURADO_MSG)}</p>"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório DODÔ — {username}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; background: #0f1115; color: #e8e8ef; margin: 0; padding: 24px; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  h2 {{ font-size: 16px; color: #9ea3b0; margin-top: 32px; border-bottom: 1px solid #2a2d36; padding-bottom: 6px; }}
  .subtitulo {{ color: #9ea3b0; margin-top: 0; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: 16px; margin-top: 16px; }}
  .card {{ background: #1a1d24; border-radius: 10px; padding: 16px 20px; min-width: 160px; flex: 1; }}
  .card .valor {{ font-size: 28px; font-weight: 700; color: #ffffff; }}
  .card .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: #9ea3b0; }}
  ul {{ padding-left: 18px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #2a2d36; font-size: 13px; }}
  .placeholder {{ color: #9ea3b0; font-style: italic; }}
  footer {{ margin-top: 40px; color: #676b78; font-size: 11px; }}
</style>
</head>
<body>
  <h1>Relatório de auditoria — @{username}</h1>
  <p class="subtitulo">Janela analisada: últimos {window_days} dias</p>

  <div class="cards">
    <div class="card"><div class="valor">{score}</div><div class="label">Score DODÔ (0-10)</div></div>
    <div class="card"><div class="valor">{engagement}</div><div class="label">Taxa de engajamento</div></div>
    <div class="card"><div class="valor">{pod_index}</div><div class="label">Índice de pods</div></div>
    <div class="card"><div class="valor">{taxa_resposta}</div><div class="label">Taxa de resposta da criadora</div></div>
  </div>

  <h2>Demografia</h2>
  <p><strong>Gênero predominante:</strong> {genero}</p>
  <p><strong>Regiões detectadas:</strong> {regioes_texto}</p>

  <h2>Antifraude</h2>
  <p><strong>Top repetidores (possíveis pods):</strong></p>
  <ul>{top_repetidores_html}</ul>

  <h2>Publis</h2>
  {publis_html}

  <h2>Comentários analisados</h2>
  <p><strong>Total coletado:</strong> {total_comentarios} — <strong>Qualificados (não rasos):</strong> {qualificados}</p>
  {gemini_section}

  <footer>Relatório gerado localmente por métricaDODÔ. Nenhum dado enviado a terceiros neste export.</footer>
</body>
</html>
"""


def generate_pdf_report(analysis: dict) -> bytes:
    """Gera o mesmo relatório em PDF, via fpdf2."""

    username = str(analysis.get("username", ""))
    window_days = analysis.get("window_days", "N/D")
    score = _fmt_float(analysis.get("score_dodo"))
    engagement = _fmt_pct(analysis.get("engagement_rate"))

    demografia = analysis.get("demografia", {}) or {}
    genero = str(demografia.get("genero_predominante", "indeterminado"))
    regioes_texto = _regioes_texto(demografia.get("regioes"))

    antifraude = analysis.get("antifraude", {}) or {}
    pod_index = _fmt_float(antifraude.get("pod_index"))
    taxa_resposta = _fmt_pct(antifraude.get("taxa_resposta_criadora"))
    top_repetidores = _top_repetidores_linhas(antifraude.get("top_repetidores"))

    publis = analysis.get("publis", []) or []
    comentarios = analysis.get("comentarios_analisados", {}) or {}
    total_comentarios = comentarios.get("total", 0)
    qualificados = comentarios.get("qualificados", 0)
    gemini_items = comentarios.get("gemini_items", []) or []

    pdf = FPDF()
    pdf.set_title(_pdf_safe(f"Relatorio DODO - {username}"))
    pdf.add_page()

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, _pdf_safe(f"Relatorio de auditoria - @{username}"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 8, _pdf_safe(f"Janela analisada: ultimos {window_days} dias"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Metricas principais", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 7, _pdf_safe(f"Score DODO (0-10): {score}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _pdf_safe(f"Taxa de engajamento: {engagement}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _pdf_safe(f"Indice de pods: {pod_index}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _pdf_safe(f"Taxa de resposta da criadora: {taxa_resposta}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Demografia", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 7, _pdf_safe(f"Genero predominante: {genero}"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 7, _pdf_safe(f"Regioes detectadas: {regioes_texto}"))
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Antifraude - top repetidores", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    if top_repetidores:
        for user, count in top_repetidores:
            pdf.cell(0, 7, _pdf_safe(f"- {user}: {count} comentarios"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 7, "Nenhum repetidor relevante identificado", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Publis", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "I", 11)
    if publis:
        for item in publis:
            pdf.multi_cell(0, 7, _pdf_safe(f"- {item}"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 7, _pdf_safe(PUBLIS_PLACEHOLDER_MSG))
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Comentarios analisados", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(
        0,
        7,
        _pdf_safe(f"Total coletado: {total_comentarios} | Qualificados (nao rasos): {qualificados}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("helvetica", "I", 10)
    if gemini_items:
        for item in gemini_items:
            texto = (
                f"- {item.get('comentario', '')} | intencao: {item.get('intencao_compra', '')} "
                f"| faixa etaria: {item.get('faixa_etaria_estimada', '')}"
            )
            pdf.multi_cell(0, 6, _pdf_safe(texto), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 6, _pdf_safe(GEMINI_NAO_CONFIGURADO_MSG))

    return bytes(pdf.output())
