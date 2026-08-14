"""Exportação do relatório de auditoria de perfil (HTML autocontido e PDF via fpdf2).

Funções puras: recebem o dicionário `analysis` (formato canônico descrito em
docs/issues/ISSUE-0004.md) e devolvem o relatório pronto para download, sem
tocar em disco, rede ou `st.session_state` — isso fica a cargo de `app.py`.
"""

import html as html_lib

from fpdf import FPDF

from src.gemini_analyzer import ADERENCIA_INDICADOR_LABELS

PUBLIS_VAZIO_MSG = (
    "Nenhuma publi ou parceria comercial identificada nas legendas coletadas nesta janela."
)
GEMINI_NAO_CONFIGURADO_MSG = "Análise de intenção via Gemini não configurada nesta sessão."

# Sprint 002 Fase 4 (BENCHMARK-001.md §4.4/§4.5, ISSUE-001.md §4.1/§4.5) —
# mensagens de estado vazio para as novas seções, seguindo o mesmo padrão de
# PUBLIS_VAZIO_MSG/GEMINI_NAO_CONFIGURADO_MSG acima.
TOP_POSTS_VAZIO_MSG = "Nenhum post disponível na amostra coletada para ranquear."
POPULAR_TAGS_VAZIO_MSG = "Nenhuma hashtag identificada nas legendas coletadas nesta janela."
BRAND_MENTIONS_VAZIO_MSG = "Nenhuma menção a outro perfil identificada nas legendas coletadas nesta janela."


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


# Seção "Proveniência e Escopo das Métricas" (Sprint 002 Fase 2, ETAPA 3.3) —
# expõe, por taxa de engajamento do contrato canônico (src/metrics.py
# build_audit_report), o tipo de cálculo, o status (disponível/indisponível
# na amostra) e a fonte, para o leitor do relatório nunca confundir "sem
# dado" com "engajamento zero" (BENCHMARK-001.md §6).
_ENGAGEMENT_RATE_PROVENANCE_LABELS = {
    "engagement_rate_by_followers": "Por seguidores",
    "engagement_rate_by_reach": "Por alcance",
    "engagement_rate_by_views": "Por views de Reels",
}
_STATUS_LABELS = {"ok": "Disponível", "indisponivel": "Indisponível nesta amostra"}


def _fmt_provenance_value(value):
    try:
        return f"{value:.2f}%"
    except (TypeError, ValueError):
        return "N/D"


def _provenance_rows(audit_report):
    """Uma linha por taxa de engajamento do contrato canônico, na ordem fixa
    do dicionário de labels acima. `audit_report` ausente (analyses geradas
    antes da Sprint 002 Fase 2, ou qualquer falha ao computá-lo) -> lista
    vazia, nunca lança exceção."""
    if not audit_report:
        return []
    metrics_map = audit_report.get("metrics") or {}

    rows = []
    for field, calculo in _ENGAGEMENT_RATE_PROVENANCE_LABELS.items():
        metric = metrics_map.get(field) or {}
        status = metric.get("status") or "indisponivel"
        rows.append(
            {
                "calculo": calculo,
                "valor": _fmt_provenance_value(metric.get("value")),
                "status": _STATUS_LABELS.get(status, status),
                "fonte": metric.get("source") or "N/D",
                "confianca": metric.get("confidence") or "N/D",
                "ressalvas": metric.get("ressalvas") or [],
            }
        )
    return rows


# Seções "Top 3 Posts", "Hashtags populares" e "Menções de marcas" (Sprint
# 002 Fase 4, ETAPA 3) — lêem os campos homônimos de src/metrics.py
# build_audit_report (top_posts/popular_tags/brand_mentions). Mesmo padrão
# de fallback gracioso de _provenance_rows: audit_report ausente ou métrica
# "indisponivel" -> lista vazia, nunca lança exceção.
def _top_posts_rows(audit_report):
    metrics_map = (audit_report or {}).get("metrics") or {}
    metric = metrics_map.get("top_posts") or {}
    if metric.get("status") != "ok":
        return []
    return metric.get("posts") or []


def _popular_tags_rows(audit_report):
    metrics_map = (audit_report or {}).get("metrics") or {}
    metric = metrics_map.get("popular_tags") or {}
    if metric.get("status") != "ok":
        return []
    return metric.get("tags") or []


def _brand_mentions_rows(audit_report):
    metrics_map = (audit_report or {}).get("metrics") or {}
    metric = metrics_map.get("brand_mentions") or {}
    if metric.get("status") != "ok":
        return [], []
    return metric.get("mentions") or [], metric.get("ressalvas") or []


def _demographic_coverage_lines(audit_report):
    """Linhas de cobertura amostral (BENCHMARK-001.md §4.4/§7.3) para anexar
    à seção Demografia: quantos comentários da amostra permitiram identificar
    gênero/região, não o universo de seguidores do perfil."""
    metrics_map = (audit_report or {}).get("metrics") or {}
    lines = []

    gender = metrics_map.get("gender_distribution") or {}
    if gender.get("status") == "ok":
        lines.append(
            f"Cobertura de gênero identificado: {_fmt_provenance_value(gender.get('value'))} da amostra de "
            f"comentários ({gender.get('total_identificados', 0)} nome(s) identificados)."
        )

    region = metrics_map.get("region_distribution") or {}
    if region.get("status") == "ok":
        lines.append(
            f"Cobertura de região identificada: {_fmt_provenance_value(region.get('value'))} da amostra de "
            "comentários."
        )

    ressalva = (gender.get("ressalvas") or region.get("ressalvas") or [None])[0]
    if ressalva:
        lines.append(ressalva)

    return lines


def _link_or_id_html(item):
    link = item.get("link")
    if link:
        escaped = html_lib.escape(str(link))
        return f'<a href="{escaped}">{escaped}</a>'
    return html_lib.escape(str(item.get("post_id", "")))


def generate_html_report(analysis: dict) -> str:
    """Gera um relatório HTML autocontido (CSS inline, sem CDN externo)."""

    username = html_lib.escape(str(analysis.get("username", "")))
    window_days = analysis.get("window_days", "N/D")
    score = _fmt_float(analysis.get("score_dodo"))
    engagement = _fmt_pct(analysis.get("engagement_rate"))

    demografia = analysis.get("demografia", {}) or {}
    genero = html_lib.escape(str(demografia.get("genero_predominante", "indeterminado")))
    regioes_texto = html_lib.escape(_regioes_texto(demografia.get("regioes")))
    coverage_html = "".join(
        f"<p>{html_lib.escape(line)}</p>" for line in _demographic_coverage_lines(analysis.get("audit_report"))
    )

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
        publis_html = "".join(
            "<li>"
            + (
                f"<a href=\"{html_lib.escape(str(item.get('link')))}\">{html_lib.escape(str(item.get('link')))}</a>"
                if item.get("link")
                else html_lib.escape(str(item.get("post_id", "")))
            )
            + f" — indícios: {html_lib.escape(', '.join(item.get('termos', [])))}"
            + (
                f" — marca(s): {html_lib.escape(', '.join(item.get('marcas', [])))}"
                if item.get("marcas")
                else ""
            )
            + "</li>"
            for item in publis
        )
    else:
        publis_html = f"<p class='placeholder'>{html_lib.escape(PUBLIS_VAZIO_MSG)}</p>"

    top_posts_rows = _top_posts_rows(analysis.get("audit_report"))
    if top_posts_rows:
        top_posts_rows_html = "".join(
            "<tr>"
            f"<td>{_link_or_id_html(item)}</td>"
            f"<td>{html_lib.escape(str(item.get('media_type') or 'N/D'))}</td>"
            f"<td>{item.get('likes_count', 0)}</td>"
            f"<td>{item.get('comments_count', 0)}</td>"
            f"<td>{item.get('engagement_absolute', 0)}</td>"
            f"<td>{_fmt_provenance_value(item.get('engagement_rate'))}</td>"
            "</tr>"
            for item in top_posts_rows
        )
        top_posts_section = f"""
        <table>
            <thead><tr><th>Post</th><th>Tipo</th><th>Curtidas</th><th>Comentários</th><th>Engajamento (abs.)</th><th>Engajamento (%)</th></tr></thead>
            <tbody>{top_posts_rows_html}</tbody>
        </table>
        """
    else:
        top_posts_section = f"<p class='placeholder'>{html_lib.escape(TOP_POSTS_VAZIO_MSG)}</p>"

    popular_tags_rows = _popular_tags_rows(analysis.get("audit_report"))
    if popular_tags_rows:
        popular_tags_html = "".join(
            f"<li>{html_lib.escape(str(item['tag']))}: {item['count']} ocorrência(s)</li>"
            for item in popular_tags_rows
        )
        popular_tags_section = f"<ul>{popular_tags_html}</ul>"
    else:
        popular_tags_section = f"<p class='placeholder'>{html_lib.escape(POPULAR_TAGS_VAZIO_MSG)}</p>"

    brand_mentions_rows, brand_mentions_ressalvas = _brand_mentions_rows(analysis.get("audit_report"))
    if brand_mentions_rows:
        brand_mentions_html = "".join(
            f"<li>{html_lib.escape(str(item['handle']))}: {item['count']} menção(ões) — "
            f"{'publi confirmada' if item['tipo'] == 'publi_confirmada' else 'menção orgânica'}</li>"
            for item in brand_mentions_rows
        )
        brand_mentions_ressalvas_html = "".join(
            f"<li>{html_lib.escape(ressalva)}</li>" for ressalva in brand_mentions_ressalvas
        )
        brand_mentions_section = f"""
        <ul>{brand_mentions_html}</ul>
        {f"<ul>{brand_mentions_ressalvas_html}</ul>" if brand_mentions_ressalvas_html else ""}
        """
    else:
        brand_mentions_section = f"<p class='placeholder'>{html_lib.escape(BRAND_MENTIONS_VAZIO_MSG)}</p>"

    comentarios = analysis.get("comentarios_analisados", {}) or {}
    total_comentarios = comentarios.get("total", 0)
    qualificados = comentarios.get("qualificados", 0)
    gemini_items = comentarios.get("gemini_items", []) or []
    parecer_comercial = comentarios.get("parecer_comercial")
    if gemini_items:
        gemini_html = "".join(
            "<tr>"
            f"<td>{html_lib.escape(str(item.get('comentario', '')))}</td>"
            f"<td>{html_lib.escape(str(item.get('intencao_compra', '')))}</td>"
            f"<td>{html_lib.escape(str(item.get('faixa_etaria_estimada', '')))}</td>"
            f"<td>{html_lib.escape(str(item.get('categoria_sentimento', '')))}</td>"
            f"<td>{html_lib.escape(', '.join(item.get('sinais_compra') or []))}</td>"
            "</tr>"
            for item in gemini_items
        )
        gemini_section = f"""
        <table>
            <thead><tr><th>Comentário</th><th>Intenção de compra</th><th>Faixa etária estimada</th><th>Sentimento</th><th>Sinais de compra</th></tr></thead>
            <tbody>{gemini_html}</tbody>
        </table>
        """
    else:
        gemini_section = f"<p class='placeholder'>{html_lib.escape(GEMINI_NAO_CONFIGURADO_MSG)}</p>"

    if parecer_comercial:
        label = html_lib.escape(
            ADERENCIA_INDICADOR_LABELS.get(parecer_comercial["indicador"], parecer_comercial["indicador"])
        )
        alertas_html = "".join(f"<li>{html_lib.escape(alerta)}</li>" for alerta in parecer_comercial.get("alertas", []))
        parecer_section = f"""
        <p><strong>Parecer de aderência comercial (brand suitability):</strong> {label}</p>
        <p>{html_lib.escape(parecer_comercial.get("resumo", ""))}</p>
        {f"<ul>{alertas_html}</ul>" if alertas_html else ""}
        """
    else:
        parecer_section = ""

    provenance_rows = _provenance_rows(analysis.get("audit_report"))
    if provenance_rows:
        provenance_html = "".join(
            "<tr>"
            f"<td>{html_lib.escape(row['calculo'])}</td>"
            f"<td>{html_lib.escape(row['valor'])}</td>"
            f"<td>{html_lib.escape(row['status'])}</td>"
            f"<td>{html_lib.escape(str(row['fonte']))}</td>"
            f"<td>{html_lib.escape(str(row['confianca']))}</td>"
            "</tr>"
            for row in provenance_rows
        )
        ressalvas_html = "".join(
            f"<li>{html_lib.escape(row['calculo'])}: {html_lib.escape(ressalva)}</li>"
            for row in provenance_rows
            for ressalva in row["ressalvas"]
        )
        provenance_section = f"""
        <table>
            <thead><tr><th>Tipo de cálculo</th><th>Valor</th><th>Status</th><th>Fonte</th><th>Confiança</th></tr></thead>
            <tbody>{provenance_html}</tbody>
        </table>
        {f"<ul>{ressalvas_html}</ul>" if ressalvas_html else ""}
        """
    else:
        provenance_section = (
            "<p class='placeholder'>Contrato canônico de métricas ainda não disponível para este relatório "
            "(análise gerada antes da Sprint 002 Fase 2, ou falha ao computá-lo).</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório DODÔ — {username}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; background: #0f1115; color: #e8e8ef; margin: 0; padding: 24px; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  h2 {{ font-size: 16px; color: #9ea3b0; margin-top: 32px; border-bottom: 1px solid #2a2d36; padding-bottom: 6px; }}
  h3 {{ font-size: 13px; color: #9ea3b0; margin-top: 20px; }}
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
    <div class="card"><div class="valor">{score}</div><div class="label">Score DODÔ</div></div>
    <div class="card"><div class="valor">{engagement}</div><div class="label">Engajamento por seguidores</div></div>
    <div class="card"><div class="valor">{pod_index}</div><div class="label">Sinal de interação coordenada</div></div>
    <div class="card"><div class="valor">{taxa_resposta}</div><div class="label">Respostas da criadora</div></div>
  </div>

  <h2>Qualidade da audiência</h2>
  <p><strong>Contas com padrão de repetição (possível sinal de interação coordenada):</strong></p>
  <ul>{top_repetidores_html}</ul>

  <h2>Qualidade e conteúdo</h2>
  <h3>Posts de maior repercussão</h3>
  {top_posts_section}
  <h3>Hashtags populares</h3>
  {popular_tags_section}
  <h3>Parcerias identificadas</h3>
  {publis_html}
  <h3>Menções de marcas</h3>
  {brand_mentions_section}

  <h2>Perfil da audiência (estimativa)</h2>
  <p><strong>Gênero predominante:</strong> {genero}</p>
  <p><strong>Regiões detectadas:</strong> {regioes_texto}</p>
  {coverage_html}

  <h2>Comentários e intenção</h2>
  <p><strong>Total coletado:</strong> {total_comentarios} — <strong>Comentários com sinal útil:</strong> {qualificados}</p>
  {parecer_section}
  {gemini_section}

  <h2>Proveniência e Escopo das Métricas</h2>
  {provenance_section}

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
    parecer_comercial = comentarios.get("parecer_comercial")
    provenance_rows = _provenance_rows(analysis.get("audit_report"))
    coverage_lines = _demographic_coverage_lines(analysis.get("audit_report"))
    top_posts_rows = _top_posts_rows(analysis.get("audit_report"))
    popular_tags_rows = _popular_tags_rows(analysis.get("audit_report"))
    brand_mentions_rows, brand_mentions_ressalvas = _brand_mentions_rows(analysis.get("audit_report"))

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
    pdf.cell(0, 7, _pdf_safe(f"Score DODO: {score}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _pdf_safe(f"Engajamento por seguidores: {engagement}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _pdf_safe(f"Sinal de interacao coordenada: {pod_index}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _pdf_safe(f"Respostas da criadora: {taxa_resposta}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Qualidade da audiencia", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 7, "Contas com padrao de repeticao (possivel sinal de interacao coordenada):", new_x="LMARGIN", new_y="NEXT")
    if top_repetidores:
        for user, count in top_repetidores:
            pdf.cell(0, 7, _pdf_safe(f"- {user}: {count} comentarios"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 7, "Nenhum repetidor relevante identificado", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Qualidade e conteudo", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 7, "Parcerias identificadas", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "I", 11)
    if publis:
        for item in publis:
            texto = f"- {item.get('link') or item.get('post_id', '')} | indicios: {', '.join(item.get('termos', []))}"
            if item.get("marcas"):
                texto += f" | marca(s): {', '.join(item.get('marcas', []))}"
            pdf.multi_cell(0, 7, _pdf_safe(texto), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 7, _pdf_safe(PUBLIS_VAZIO_MSG), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Posts de maior repercussao", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    if top_posts_rows:
        for item in top_posts_rows:
            engajamento_pct = _fmt_provenance_value(item.get("engagement_rate"))
            texto = (
                f"- {item.get('link') or item.get('post_id', '')} | tipo: {item.get('media_type') or 'N/D'} "
                f"| curtidas: {item.get('likes_count', 0)} | comentarios: {item.get('comments_count', 0)} "
                f"| engajamento abs.: {item.get('engagement_absolute', 0)} | engajamento: {engajamento_pct}"
            )
            pdf.multi_cell(0, 6, _pdf_safe(texto), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 6, _pdf_safe(TOP_POSTS_VAZIO_MSG), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Hashtags populares", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    if popular_tags_rows:
        for item in popular_tags_rows:
            pdf.multi_cell(
                0, 6, _pdf_safe(f"- {item['tag']}: {item['count']} ocorrencia(s)"), new_x="LMARGIN", new_y="NEXT"
            )
    else:
        pdf.multi_cell(0, 6, _pdf_safe(POPULAR_TAGS_VAZIO_MSG), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Mencoes de marcas", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    if brand_mentions_rows:
        for item in brand_mentions_rows:
            tipo = "publi confirmada" if item["tipo"] == "publi_confirmada" else "mencao organica"
            texto = f"- {item['handle']}: {item['count']} mencao(oes) - {tipo}"
            pdf.multi_cell(0, 6, _pdf_safe(texto), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "I", 9)
        for ressalva in brand_mentions_ressalvas:
            pdf.multi_cell(0, 5, _pdf_safe(f"  Ressalva: {ressalva}"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 6, _pdf_safe(BRAND_MENTIONS_VAZIO_MSG), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Perfil da audiencia (estimativa)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 7, _pdf_safe(f"Genero predominante: {genero}"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 7, _pdf_safe(f"Regioes detectadas: {regioes_texto}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "I", 10)
    for line in coverage_lines:
        pdf.multi_cell(0, 6, _pdf_safe(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Comentarios e intencao", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(
        0,
        7,
        _pdf_safe(f"Total coletado: {total_comentarios} | Comentarios com sinal util: {qualificados}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    if parecer_comercial:
        label = ADERENCIA_INDICADOR_LABELS.get(parecer_comercial["indicador"], parecer_comercial["indicador"])
        pdf.set_font("helvetica", "B", 10)
        pdf.multi_cell(0, 6, _pdf_safe(f"Parecer de aderencia comercial (brand suitability): {label}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, _pdf_safe(parecer_comercial.get("resumo", "")), new_x="LMARGIN", new_y="NEXT")
        for alerta in parecer_comercial.get("alertas", []):
            pdf.multi_cell(0, 6, _pdf_safe(f"- Alerta: {alerta}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.set_font("helvetica", "I", 10)
    if gemini_items:
        for item in gemini_items:
            texto = (
                f"- {item.get('comentario', '')} | intencao: {item.get('intencao_compra', '')} "
                f"| faixa etaria: {item.get('faixa_etaria_estimada', '')}"
            )
            sentimento = item.get("categoria_sentimento")
            if sentimento:
                texto += f" | sentimento: {sentimento}"
            sinais = item.get("sinais_compra")
            if sinais:
                texto += f" | sinais de compra: {', '.join(sinais)}"
            pdf.multi_cell(0, 6, _pdf_safe(texto), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 6, _pdf_safe(GEMINI_NAO_CONFIGURADO_MSG))
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Proveniencia e Escopo das Metricas", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    if provenance_rows:
        for row in provenance_rows:
            texto = (
                f"- {row['calculo']}: {row['valor']} | status: {row['status']} "
                f"| fonte: {row['fonte']} | confianca: {row['confianca']}"
            )
            pdf.multi_cell(0, 6, _pdf_safe(texto), new_x="LMARGIN", new_y="NEXT")
            for ressalva in row["ressalvas"]:
                pdf.set_font("helvetica", "I", 9)
                pdf.multi_cell(0, 5, _pdf_safe(f"  Ressalva: {ressalva}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("helvetica", "", 10)
    else:
        pdf.multi_cell(
            0,
            6,
            _pdf_safe(
                "Contrato canonico de metricas ainda nao disponivel para este relatorio "
                "(analise gerada antes da Sprint 002 Fase 2, ou falha ao computa-lo)."
            ),
        )

    return bytes(pdf.output())
