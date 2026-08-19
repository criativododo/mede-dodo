"""Motor de métricas autorais (ISSUE-004) — Rodada 1 (ER Branding) e Rodadas
2/3 (tipologia/P1, P2, P3, BQI, CI, densidade de patrocínio, parecer
editorial), todas aprovadas pelo Dani em 2026-08-15 com base em
`BENCHMARK-METRICS-001.md §6-9`.

100% Python puro, sem Streamlit, banco ou rede — ver ADR-001 (View Pura) e
ADR-002. Este módulo nunca classifica comentário bruto (isso é ISSUE-005 —
`ai_local.py`/`ai_gemini.py`); recebe `comment_labels` já resolvido. O Pilar
2 (retenção visual/alcance qualificado) exige `save_rate`/`share_rate`/`vtr`/
`qualified_reach_rate`, sinais que a coleta pública via Instaloader não
expõe — por isso `bqi`/`ci`/`editorial_opinion` retornam `indisponivel`
sempre que esses insumos não vierem explicitamente no payload; nunca são
aproximados por outro sinal (SPEC-001.md §4.4, DUMMY.md §5).
"""

import statistics

METHOD_VERSION = "BMQ-001-v2.0.0-r1"

ACTION_WEIGHTS = {"comments": 3, "shares": 3, "saves": 2, "likes": 3}
FORMAT_WEIGHTS = {"carrossel": 1.20, "foto": 1.00, "reel": 0.80}


def weighted_interactions(post: dict) -> float:
    """Soma comentários, compartilhamentos e curtidas com peso 3 e salvamentos com peso 2."""
    return (
        ACTION_WEIGHTS["comments"] * post.get("comments", 0)
        + ACTION_WEIGHTS["shares"] * post.get("shares", 0)
        + ACTION_WEIGHTS["saves"] * post.get("saves", 0)
        + ACTION_WEIGHTS["likes"] * post.get("likes", 0)
    )


def format_factor(post_format):
    """Fator de formato aprovado (carrossel/foto/reel), ou `None` para formato
    desconhecido — nunca um peso implícito."""
    return FORMAT_WEIGHTS.get(post_format)


def resolve_denominator(post: dict, followers_count, allow_followers_fallback: bool = True):
    """Prioriza `reach_unique`; recorre a `followers_count` só se permitido e disponível.

    Retorna `(valor, modo)`, com `modo` em `"reach_unique"`, `"followers"` ou
    `"unavailable"`. `reach_unique` presente mas `<= 0` é tratado como ausente,
    nunca como divisor válido (evita divisão por zero silenciosa).
    """
    reach = post.get("reach_unique")
    if reach is not None and reach > 0:
        return reach, "reach_unique"
    if allow_followers_fallback and followers_count:
        return followers_count, "followers"
    return None, "unavailable"


def _denominator_mode_label(modes_used: set) -> str:
    known_modes = modes_used - {"unavailable"}
    if not known_modes:
        return "unavailable"
    if len(known_modes) > 1:
        return "mixed"
    return next(iter(known_modes))


def _prepare_posts(payload: dict) -> dict:
    """Resolve denominador e fator de formato de cada post (Stories vivem em
    outra chave do payload e nunca passam por aqui)."""
    profile = payload.get("profile") or {}
    followers_count = profile.get("followers_count")
    options = payload.get("options") or {}
    allow_fallback = options.get("denominator_preference", "reach_unique_then_followers") != "reach_unique_only"

    included = []
    excluded_unknown_format = []
    excluded_no_denominator = []
    modes_used = set()
    warnings = []

    for post in payload.get("posts") or []:
        post_id = post.get("post_id")
        factor = format_factor(post.get("format"))
        if factor is None:
            excluded_unknown_format.append(post_id)
            warnings.append(
                f"post {post_id}: formato desconhecido — excluído do ER Branding, nenhum peso implícito atribuído"
            )
            continue

        denominator, mode = resolve_denominator(post, followers_count, allow_fallback)
        modes_used.add(mode)
        if mode == "unavailable":
            excluded_no_denominator.append(post_id)
            warnings.append(
                f"post {post_id}: sem alcance único e sem fallback de seguidores disponível — excluído do ER Branding"
            )
            continue
        if mode == "followers":
            warnings.append(f"post {post_id}: alcance único ausente — usando seguidores como denominador histórico")

        included.append(
            {
                "post_id": post_id,
                "format": post.get("format"),
                "factor": factor,
                "denominator": denominator,
                "denominator_mode": mode,
                "weighted_interactions": weighted_interactions(post),
            }
        )

    return {
        "included": included,
        "excluded_unknown_format": excluded_unknown_format,
        "excluded_no_denominator": excluded_no_denominator,
        "modes_used": modes_used,
        "warnings": warnings,
    }


def calculate_er_branding(payload: dict) -> dict:
    """Agrega o ER Branding da Rodada 1 — sem Stories, com denominador declarado explicitamente."""
    prepared = _prepare_posts(payload)
    included = prepared["included"]

    numerator = sum(p["factor"] * p["weighted_interactions"] for p in included)
    denominator_total = sum(p["factor"] * p["denominator"] for p in included)

    mode = _denominator_mode_label(prepared["modes_used"])
    value = round(100 * numerator / denominator_total, 2) if denominator_total > 0 else None

    return {
        "value": value,
        "unit": "pct",
        "denominator": mode,
        "content_scope": "all_content_without_stories",
        "format_weights": dict(FORMAT_WEIGHTS),
        "posts_n": len(included),
        "posts_excluded_unknown_format_n": len(prepared["excluded_unknown_format"]),
        "posts_excluded_no_denominator_n": len(prepared["excluded_no_denominator"]),
        "warnings": prepared["warnings"],
    }


def calculate_er_by_format(payload: dict) -> dict:
    """Corte comparável por formato — mesmo núcleo do ER Branding, sem o fator
    de formato (o grupo já é homogêneo)."""
    included = _prepare_posts(payload)["included"]

    by_format = {fmt: {"value": None, "posts_n": 0} for fmt in FORMAT_WEIGHTS}
    for fmt in FORMAT_WEIGHTS:
        posts = [p for p in included if p["format"] == fmt]
        if not posts:
            continue
        numerator = sum(p["weighted_interactions"] for p in posts)
        denominator_total = sum(p["denominator"] for p in posts)
        by_format[fmt] = {
            "value": round(100 * numerator / denominator_total, 2) if denominator_total > 0 else None,
            "posts_n": len(posts),
        }
    return by_format


def calculate_stories_context(payload: dict) -> dict:
    """Stories são um sinal contextual separado — nunca entram no numerador ou
    denominador do ER Branding principal."""
    stories = payload.get("stories") or []
    return {"status": "separate_contextual_signal", "stories_n": len(stories)}


def _calculate_coverage(payload: dict, posts_used_in_er_n: int) -> dict:
    posts = payload.get("posts") or []
    total = len(posts)
    with_reach = sum(1 for p in posts if (p.get("reach_unique") or 0) > 0)
    return {
        "posts_total_n": total,
        "posts_with_reach_unique_n": with_reach,
        "reach_unique_coverage_pct": round(100 * with_reach / total, 1) if total else 0.0,
        "posts_used_in_er_n": posts_used_in_er_n,
    }


# --- Rodada 2: Tipologia A/B/C/D (V_AB, Pilar 1) -----------------------------------------------------------

def calculate_comment_typology(comment_labels: dict) -> dict:
    """V_AB e Pilar 1 (conversação e afinidade) a partir de rótulos A/B/C/D já
    classificados pela ISSUE-005 — nunca reclassifica texto bruto aqui
    (BENCHMARK-METRICS-001.md §3, §6.1)."""
    a = comment_labels.get("A") or 0
    b = comment_labels.get("B") or 0
    c = comment_labels.get("C") or 0
    d = comment_labels.get("D") or 0
    total = a + b + c + d
    if total == 0:
        return {"status": "indisponivel", "v_ab": None, "p1": None, "counts": dict(comment_labels), "total_n": 0}

    v_ab = round(100 * (a + b) / total, 1)
    ab = a + b
    term1 = 0.60 * ab / total
    term2 = 0.25 * (a / ab) if ab > 0 else 0.0
    term3 = 0.15 * (b / ab) if ab > 0 else 0.0
    p1 = round(100 * (term1 + term2 + term3), 2)

    return {
        "status": "ok",
        "v_ab": v_ab,
        "p1": p1,
        "counts": {"A": a, "B": b, "C": c, "D": d},
        "total_n": total,
    }


def calculate_noise_reduction(comment_labels: dict) -> dict:
    """Pilar 3 (redutor de ruído) — proporção de `D` e de spam sobre o total
    de comentários classificados (BENCHMARK-METRICS-001.md §6.1)."""
    a = comment_labels.get("A") or 0
    b = comment_labels.get("B") or 0
    c = comment_labels.get("C") or 0
    d = comment_labels.get("D") or 0
    spam = comment_labels.get("spam") or 0
    total = a + b + c + d
    if total == 0:
        return {"status": "indisponivel", "value": None}

    term1 = 0.70 * (1 - d / total)
    term2 = 0.30 * (1 - spam / total)
    return {"status": "ok", "value": round(100 * (term1 + term2), 2)}


# --- Rodada 2: Pilar 2 (retenção visual/alcance qualificado) -----------------------------------------------------------

_P2_BOUNDS = {
    "save_rate": (0.005, 0.04),
    "share_rate": (0.002, 0.02),
    "vtr": (0.10, 0.40),
    "qualified_reach_rate": (0.50, 0.90),
}
_P2_WEIGHTS = {"save_rate": 0.30, "share_rate": 0.25, "vtr": 0.25, "qualified_reach_rate": 0.20}


def _normalize_p2_signal(value: float, bounds: tuple) -> float:
    lower, upper = bounds
    clipped = max(0.0, min(1.0, (value - lower) / (upper - lower)))
    return 100 * clipped


def calculate_visual_retention(p2_inputs: dict) -> dict:
    """Pilar 2 — exige `save_rate`/`share_rate`/`vtr`/`qualified_reach_rate`
    (frações 0-1) já resolvidos. Estes sinais não são expostos pela API
    pública do Instagram via Instaloader — sem todos os quatro, retorna
    `indisponivel` explícito, nunca aproxima com outro sinal disponível."""
    if any(p2_inputs.get(chave) is None for chave in _P2_BOUNDS):
        return {"status": "indisponivel", "value": None}

    total = sum(
        _P2_WEIGHTS[chave] * _normalize_p2_signal(p2_inputs[chave], bounds)
        for chave, bounds in _P2_BOUNDS.items()
    )
    return {"status": "ok", "value": round(total, 2)}


# --- Rodada 2: BQI (combinação dos pilares) -----------------------------------------------------------

def _bqi_band(value: float) -> str:
    if value >= 80:
        return "excelente"
    if value >= 65:
        return "saudavel"
    if value >= 50:
        return "alerta"
    return "nao_recomendada"


def calculate_bqi(p1, p2, p3=None) -> dict:
    """BQI = clip(100 × BQI_guarded / 85, 0, 100), com `BQI_core=0,45P1+0,40P2`
    e `BQI_guarded=BQI_core×(0,85+0,15×P3/100)` (BENCHMARK-METRICS-001.md
    §6.2). Sem P1 ou P2, retorna `indisponivel` — nunca zero silencioso."""
    if p1 is None or p2 is None:
        return {"status": "indisponivel", "value": None, "band": None}

    warning = None
    p3_efetivo = p3
    if p3_efetivo is None:
        p3_efetivo = 100.0
        warning = "Pilar 3 (redutor de ruído) indisponível — BQI calculado sem penalização de ruído."

    bqi_core = 0.45 * p1 + 0.40 * p2
    bqi_guarded = bqi_core * (0.85 + 0.15 * p3_efetivo / 100)
    bqi = max(0.0, min(100.0, 100 * bqi_guarded / 85))

    result = {"status": "ok", "value": round(bqi, 1), "band": _bqi_band(bqi)}
    if warning:
        result["warning"] = warning
    return result


# --- Rodada 3: Densidade de patrocínio (SD) -----------------------------------------------------------

def _sd_band(value: float) -> str:
    if value <= 20:
        return "saudavel"
    if value <= 25:
        return "toleravel"
    if value <= 33:
        return "alerta"
    return "nao_recomendado"


def calculate_sponsor_density(posts: list) -> dict:
    """SD = unidades patrocinadas / unidades comparáveis (feed/Reel com
    formato reconhecido — Stories e formato desconhecido nunca contam como
    comparáveis). Único bloco da Rodada 3 alimentável com dado real coletado
    hoje, via `is_sponsored` (BENCHMARK-METRICS-001.md §7.2)."""
    comparaveis = [post for post in posts if (post.get("format") or "").lower() in FORMAT_WEIGHTS]
    total = len(comparaveis)
    if total == 0:
        return {"status": "indisponivel", "value": None, "band": None, "unidades_comparaveis_n": 0, "unidades_patrocinadas_n": 0}

    patrocinadas = sum(1 for post in comparaveis if post.get("is_sponsored"))
    value = round(100 * patrocinadas / total, 1)
    return {
        "status": "ok",
        "value": value,
        "unit": "pct",
        "band": _sd_band(value),
        "unidades_comparaveis_n": total,
        "unidades_patrocinadas_n": patrocinadas,
    }


# --- Rodada 3: Consistência (CI) -----------------------------------------------------------

def _ci_band(value: float) -> str:
    if value >= 75:
        return "consistente"
    if value >= 60:
        return "aceitavel"
    return "instavel"


def calculate_consistency(weekly_values: list, floor: float | None) -> dict:
    """CI = 100×[0,70×(1-clip(IQR/2M,0,1)) + 0,30×(semanas acima do
    piso/semanas observadas)] (BENCHMARK-METRICS-001.md §7.1). Exige um
    `floor` explícito (nunca inventado por este código) e ao menos duas
    semanas de observação; caso contrário, `indisponivel`. Quantis calculados
    via `statistics.quantiles(..., method="exclusive")` — método versionado
    aqui porque a fonte não especifica a interpolação."""
    if floor is None or not weekly_values or len(weekly_values) < 2:
        return {"status": "indisponivel", "value": None, "band": None}

    median = statistics.median(weekly_values)
    if median == 0:
        return {"status": "indisponivel", "value": None, "band": None}

    q1, _, q3 = statistics.quantiles(weekly_values, n=4, method="exclusive")
    iqr = q3 - q1
    dispersao = max(0.0, min(1.0, iqr / (2 * median)))

    semanas_acima_do_piso = sum(1 for valor in weekly_values if valor >= floor)
    cobertura_piso = semanas_acima_do_piso / len(weekly_values)

    ci = 100 * (0.70 * (1 - dispersao) + 0.30 * cobertura_piso)
    ci = max(0.0, min(100.0, ci))
    return {"status": "ok", "value": round(ci, 1), "band": _ci_band(ci)}


# --- Rodada 3: Parecer editorial combinado -----------------------------------------------------------

def calculate_editorial_opinion(bqi, v_ab, ci, sd, d_pct, viral_dependency: bool = False, blockers: dict | None = None) -> dict:
    """Veredito matemático combinando BQI/V_AB/CI/SD/D% e bloqueadores
    absolutos (BENCHMARK-METRICS-001.md §9). Bloqueador ativo sempre vence,
    independente do BQI. Sem BQI/V_AB/CI/SD resolvidos, `indisponivel` —
    nunca um veredito fabricado sobre dado ausente."""
    blockers = blockers or {}
    if any(blockers.values()):
        return {"status": "ok", "veredito": "nao_recomendada", "reason": "bloqueador_ativo"}

    if bqi is None or v_ab is None or ci is None or sd is None:
        return {"status": "indisponivel", "veredito": None}

    if viral_dependency:
        return {"status": "ok", "veredito": "nao_recomendada_branding", "reason": "dependencia_de_viral"}

    d_ok = d_pct is None or d_pct <= 35
    if bqi >= 80 and v_ab >= 40 and ci >= 75 and sd <= 20 and d_ok:
        return {"status": "ok", "veredito": "recomendada_alta_afinidade"}
    if bqi >= 65 and v_ab >= 30 and ci >= 60 and sd <= 25:
        return {"status": "ok", "veredito": "recomendada_com_ressalvas"}
    if 50 <= bqi <= 64 and v_ab < 30 and ci < 60 and sd > 25:
        return {"status": "ok", "veredito": "nao_recomendada_branding"}
    return {"status": "ok", "veredito": "nao_recomendada"}


def calculate_metrics(payload: dict) -> dict:
    """Ponto de entrada do motor. Rodada 1 (ER Branding) sempre calcula a
    partir de `posts`/`profile`. Rodadas 2/3 calculam quando o payload traz
    `comment_labels`/`p2_inputs`/`weekly_consistency`; sem esses insumos,
    retornam `indisponivel` explícito — nunca inferidos por este código."""
    er_branding = calculate_er_branding(payload)
    er_by_format = calculate_er_by_format(payload)
    stories_context = calculate_stories_context(payload)
    coverage = _calculate_coverage(payload, er_branding["posts_n"])

    status = "ok" if er_branding["value"] is not None else "insufficient_data"

    comment_labels = payload.get("comment_labels") or {}
    comment_typology = calculate_comment_typology(comment_labels)
    p3 = calculate_noise_reduction(comment_labels)
    p2 = calculate_visual_retention(payload.get("p2_inputs") or {})
    bqi = calculate_bqi(
        comment_typology.get("p1"),
        p2.get("value"),
        p3.get("value"),
    )
    sponsor_density = calculate_sponsor_density(payload.get("posts") or [])

    weekly = payload.get("weekly_consistency") or {}
    ci = calculate_consistency(weekly.get("values") or [], weekly.get("floor"))

    d_pct = None
    if comment_typology.get("status") == "ok":
        d_pct = round(100 * comment_typology["counts"]["D"] / comment_typology["total_n"], 1)

    editorial_opinion = calculate_editorial_opinion(
        bqi.get("value"),
        comment_typology.get("v_ab"),
        ci.get("value"),
        sponsor_density.get("value"),
        d_pct,
        viral_dependency=bool((payload.get("options") or {}).get("viral_dependency")),
        blockers=payload.get("blockers"),
    )

    warnings = list(er_branding["warnings"])
    if bqi.get("warning"):
        warnings.append(bqi["warning"])

    provenance = {
        "formula_version": METHOD_VERSION,
        "window_days": (payload.get("window") or {}).get("days"),
        "posts_n": len(payload.get("posts") or []),
        "posts_used_in_er_n": er_branding["posts_n"],
        "denominator_mode": er_branding["denominator"],
    }

    return {
        "status": status,
        "method_version": METHOD_VERSION,
        "er_branding": er_branding,
        "er_by_format": er_by_format,
        "stories_context": stories_context,
        "denominator_mode": er_branding["denominator"],
        "coverage": coverage,
        "provenance": provenance,
        "warnings": warnings,
        "comment_typology": comment_typology,
        "bqi": bqi,
        "ci": ci,
        "sponsor_density": sponsor_density,
        "editorial_opinion": editorial_opinion,
    }
