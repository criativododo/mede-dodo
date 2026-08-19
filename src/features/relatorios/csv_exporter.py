"""Exportador CSV (ISSUE-006) — auditoria tabular do relatório métricaDODÔ.

100% Python puro, sem rede/banco/disco/Streamlit (SPEC-001 §3.5, DUMMY.md §4).
Recebe o payload já resolvido (mesmo shape de `st.session_state.report` em
`src/app.py`) e nunca recalcula métricas nem fabrica valores ausentes — campos
sem dado disponível são explicitados como `indisponivel`, nunca omitidos ou
zerados silenciosamente.
"""

import csv
import io

_PLACEHOLDER = "indisponivel"

_POST_FIELDS = [
    "post_id", "format", "published_at", "likes", "comments",
    "shares", "saves", "reach", "is_sponsored",
]


def _value_or_placeholder(value) -> str:
    return _PLACEHOLDER if value is None else str(value)


def generate_csv_report(data: dict) -> bytes:
    """Gera o CSV em 3 blocos (metadados, métricas consolidadas, posts) e
    retorna bytes `utf-8-sig` (compatível com Excel/Google Sheets)."""
    perfil = data.get("perfil") or {}
    janela = data.get("janela") or {}
    metricas = data.get("metricas") or {}
    provenance = data.get("provenance") or {}
    posts = data.get("posts") or []

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["=== METADADOS DA AUDITORIA ==="])
    writer.writerow(["campo", "valor"])
    writer.writerow(["perfil", _value_or_placeholder(perfil.get("username"))])
    writer.writerow(["marca_contratante", _value_or_placeholder(perfil.get("marca_contratante"))])
    writer.writerow(["janela_dias", _value_or_placeholder(janela.get("dias"))])
    writer.writerow(["formula_version", _value_or_placeholder(provenance.get("method_version"))])
    writer.writerow(["gerado_em_utc", _value_or_placeholder(provenance.get("generated_at_utc"))])
    writer.writerow([])

    writer.writerow(["=== METRICAS CONSOLIDADAS ==="])
    writer.writerow(["metrica", "valor"])
    writer.writerow(["er_branding_pct", _value_or_placeholder(metricas.get("er_branding"))])
    writer.writerow(["bqi", _value_or_placeholder(metricas.get("bqi"))])
    writer.writerow(["ci_pct", _value_or_placeholder(metricas.get("ci"))])
    writer.writerow(["sd_pct", _value_or_placeholder(metricas.get("sd"))])
    writer.writerow([])

    writer.writerow(["=== POSTS ANALISADOS ==="])
    writer.writerow(_POST_FIELDS)
    for post in posts:
        writer.writerow([post.get(field) for field in _POST_FIELDS])

    return buffer.getvalue().encode("utf-8-sig")
