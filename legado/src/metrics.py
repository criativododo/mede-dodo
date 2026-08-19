import re
from collections import Counter, defaultdict

from src import demographics
from src.filters import BRAND_MENTION_PATTERN, SPONSORED_PATTERNS, is_shallow_comment
from src.scoring import get_influencer_tier

_HASHTAG_PATTERN = re.compile(r"#(\w+)", re.UNICODE)

# Sprint 002 Fase 4 (BENCHMARK-001.md §4.4/§7.3): toda distribuição
# demográfica derivada de comentários precisa carregar esta ressalva — os
# comentários públicos coletados são uma amostra, não o universo de
# seguidores do perfil (ISSUE-001.md §7.3, Meta Insights doc referenciada no
# benchmark).
_DEMOGRAPHIC_SAMPLE_RESSALVA = (
    "Os dados demográficos refletem apenas a amostragem de comentários "
    "públicos capturados nesta coleta — não representam o universo total "
    "de seguidores do perfil (BENCHMARK-001.md §4.4/§7.3)."
)

# Contrato canônico de métricas e proveniência (Sprint 002 — BENCHMARK-001.md §6/§7,
# ISSUE-001.md §5.3/§5.4/§6.2). Cada métrica é um objeto autodescritivo (value/kind/
# source/confidence/ressalvas) em vez de um número solto, para que quem consome o
# relatório saiba se o valor foi observado, derivado localmente, estimado ou vindo de
# uma fonte externa — e para nunca confundir "não temos esse dado" com um 0 silencioso.
_ENGAGEMENT_INCLUDED_ACTIONS = ["likes", "comments"]


def _interactions(post):
    return (post.get("likes_count") or 0) + (post.get("comments_count") or 0)


def _unavailable_engagement_metric(source, denominator, post_count, ressalva):
    return {
        "value": None,
        "unit": "percent",
        "kind": None,
        "source": source,
        "confidence": None,
        "denominator": denominator,
        "included_actions": _ENGAGEMENT_INCLUDED_ACTIONS,
        "post_count": post_count,
        "status": "indisponivel",
        "ressalvas": [ressalva],
    }


def calc_engagement_rate_by_followers(posts, followers_count):
    """ER por seguidores (BENCHMARK-001.md §7.1, ISSUE-001.md §5.3): média de
    ((likes + comments) / followers) * 100 por post — a taxa "clássica" de
    ranking público (referência HypeAuditor). Retorna métrica "indisponivel"
    (value=None) em vez de 0 quando não há posts ou seguidores na amostra."""
    source = "local_scraper_sample"
    denominator = "followers_count"

    if not posts or not followers_count or followers_count <= 0:
        return _unavailable_engagement_metric(
            source,
            denominator,
            len(posts),
            "Sem posts na amostra ou seguidores desconhecidos/zero — taxa por seguidores indisponível.",
        )

    ratios = [(_interactions(post) / followers_count) * 100 for post in posts]

    return {
        "value": sum(ratios) / len(ratios),
        "unit": "percent",
        "kind": "derived",
        "source": source,
        "confidence": "high",
        "denominator": denominator,
        "included_actions": _ENGAGEMENT_INCLUDED_ACTIONS,
        "post_count": len(posts),
        "status": "ok",
        "ressalvas": [],
    }


def calc_engagement_rate_by_reach(posts):
    """ER por alcance (BENCHMARK-001.md §7.1, ISSUE-001.md §5.4):
    total_interactions / total_reach * 100, somado apenas sobre os posts da
    amostra que têm `estimated_reach` (a coleta local atual, via
    Instaloader/scraping público, não fornece alcance — esse dado exige
    Instagram Insights autenticado). Nunca lança exceção; sem nenhum post
    com alcance, a métrica volta "indisponivel"."""
    source = "post_level_estimated_reach"
    denominator = "estimated_reach"

    posts_com_alcance = [post for post in posts if post.get("estimated_reach")]
    total_reach = sum(post["estimated_reach"] for post in posts_com_alcance)

    if not posts_com_alcance or not total_reach:
        return _unavailable_engagement_metric(
            source,
            denominator,
            0,
            "Nenhum post da amostra possui alcance estimado — a coleta atual (scraping "
            "público) não fornece esse dado; requer Instagram Insights autenticado.",
        )

    total_interactions = sum(_interactions(post) for post in posts_com_alcance)

    return {
        "value": (total_interactions / total_reach) * 100,
        "unit": "percent",
        "kind": "derived",
        "source": source,
        "confidence": "medium",
        "denominator": denominator,
        "included_actions": _ENGAGEMENT_INCLUDED_ACTIONS,
        "post_count": len(posts_com_alcance),
        "status": "ok",
        "ressalvas": [],
    }


def calc_engagement_rate_by_views(posts):
    """ER por views (BENCHMARK-001.md §7.1/§4.2, ISSUE-001.md §5.4), restrita a
    posts de vídeo/Reels: total_interactions / total_views * 100, somado só
    sobre os posts da amostra com `raw.is_video=True` e `raw.video_view_count`
    válido (Sprint 002 Fase 2: `src/scraper.py` popula esses dois campos a
    partir de `post.is_video`/`post.video_view_count` do Instaloader). Nunca
    lança exceção; sem nenhum vídeo com views na amostra, a métrica fica
    "indisponivel" em vez de inventar um 0."""
    source = "post_level_video_view_count"
    denominator = "video_view_count"

    reels_com_views = [
        post
        for post in posts
        if (post.get("raw") or {}).get("is_video") and (post.get("raw") or {}).get("video_view_count")
    ]
    total_views = sum((post.get("raw") or {})["video_view_count"] for post in reels_com_views)

    if not reels_com_views or not total_views:
        return _unavailable_engagement_metric(
            source,
            denominator,
            0,
            "Nenhum post de vídeo/Reels com video_view_count coletado na amostra — "
            "requer raw.is_video=True e raw.video_view_count válido.",
        )

    total_interactions = sum(_interactions(post) for post in reels_com_views)

    return {
        "value": (total_interactions / total_views) * 100,
        "unit": "percent",
        "kind": "derived",
        "source": source,
        "confidence": "medium",
        "denominator": denominator,
        "included_actions": _ENGAGEMENT_INCLUDED_ACTIONS,
        "post_count": len(reels_com_views),
        "status": "ok",
        "ressalvas": [],
    }


def _extract_comments(posts):
    """Achata post.raw.comments de todos os posts da amostra, anexando
    post_id a cada comentário (o mesmo formato usado por app.py para montar
    all_comments_flat). Nunca lança exceção: posts sem raw/comments viram
    lista vazia."""
    all_comments = []
    for post in posts:
        raw_comments = (post.get("raw") or {}).get("comments", []) or []
        for comment in raw_comments:
            all_comments.append({**comment, "post_id": post.get("post_id")})
    return all_comments


def classify_pod_risk(pod_index_percent):
    """Classificação de risco do pod_index (BENCHMARK-001.md §4.3/§7.2):
    'baixo' < 10%, 'médio' 10-25%, 'alto' > 25%."""
    if pod_index_percent > 25:
        return "alto"
    if pod_index_percent >= 10:
        return "medio"
    return "baixo"


def calc_pod_index_metric(posts):
    """pod_index (BENCHMARK-001.md §4.3) no formato do contrato canônico:
    reaproveita `calc_pod_index` sobre os comentaristas extraídos de
    post.raw.comments, expondo o valor em percentual, os top repetidores e a
    classificação de risco. 'indisponivel' quando a amostra não tem nenhum
    comentário coletado."""
    metrics_posts = [
        {
            "post_id": post.get("post_id"),
            "commenters": [c.get("username") for c in (post.get("raw") or {}).get("comments", []) or []],
        }
        for post in posts
    ]
    pod_result = calc_pod_index(metrics_posts)

    if not pod_result["total_comentarios"]:
        return {
            "value": None,
            "unit": "percent",
            "kind": None,
            "source": "local_comment_sample",
            "confidence": None,
            "status": "indisponivel",
            "top_repetidores": {},
            "risk": None,
            "ressalvas": ["Sem comentários coletados na amostra — pod_index indisponível."],
        }

    pod_index_percent = pod_result["pod_index"] * 100

    return {
        "value": pod_index_percent,
        "unit": "percent",
        "kind": "derived",
        "source": "local_comment_sample",
        "confidence": "medium",
        "status": "ok",
        "top_repetidores": pod_result["top_repetidores"],
        "risk": classify_pod_risk(pod_index_percent),
        "ressalvas": [],
    }


def calc_shallow_ratio_metric(posts):
    """shallow_ratio (BENCHMARK-001.md §4.3): proporção de comentários rasos
    (filters.is_shallow_comment) descartados localmente antes de qualquer
    envio ao Gemini (DUMMY.md #2). 'indisponivel' sem comentários na
    amostra."""
    comments = _extract_comments(posts)
    total = len(comments)

    if not total:
        return {
            "value": None,
            "unit": "percent",
            "kind": None,
            "source": "local_comment_sample",
            "confidence": None,
            "status": "indisponivel",
            "shallow_count": 0,
            "total_count": 0,
            "ressalvas": ["Sem comentários coletados na amostra — shallow_ratio indisponível."],
        }

    shallow_count = sum(1 for comment in comments if is_shallow_comment(comment.get("texto", "")))

    return {
        "value": (shallow_count / total) * 100,
        "unit": "percent",
        "kind": "derived",
        "source": "local_comment_sample",
        "confidence": "high",
        "status": "ok",
        "shallow_count": shallow_count,
        "total_count": total,
        "ressalvas": [],
    }


def calc_creator_response_rate_metric(posts):
    """creator_response_rate (BENCHMARK-001.md §4.3): proporção de
    comentários que receberam resposta da própria criadora, a partir do
    sinal `respondido` já populado por src/scraper.py (real) ou pelo Modo
    Demonstração. 'indisponivel' sem comentários na amostra."""
    comments = _extract_comments(posts)
    total = len(comments)

    if not total:
        return {
            "value": None,
            "unit": "percent",
            "kind": None,
            "source": "local_comment_sample",
            "confidence": None,
            "status": "indisponivel",
            "responded_count": 0,
            "total_count": 0,
            "ressalvas": ["Sem comentários coletados na amostra — taxa de resposta da criadora indisponível."],
        }

    responded_count = sum(1 for comment in comments if comment.get("respondido"))

    return {
        "value": (responded_count / total) * 100,
        "unit": "percent",
        "kind": "derived",
        "source": "local_comment_sample",
        "confidence": "medium",
        "status": "ok",
        "responded_count": responded_count,
        "total_count": total,
        # SPEC-005 §4.5: nomes canônicos do contrato de threads — `comments`
        # aqui já são só comentários raiz (post.get_comments() do Instaloader
        # não desce para as respostas em `answers`/`edge_threaded_comments`;
        # `respondido` já é derivado dessa evidência de thread em
        # src/scraper.py), então root_comments_evaluable/root_comments_with_
        # creator_reply são apenas aliases legíveis de total_count/
        # responded_count, sem recontagem.
        "root_comments_evaluable": total,
        "root_comments_with_creator_reply": responded_count,
        "reply_detection_method": "thread_evidence_v1",
        "ressalvas": [
            "'respondido' é observado apenas quando a coleta identifica reply da "
            "própria criadora no post — não distingue resposta pública de privada."
        ],
    }


_AUTHENTICITY_METHOD_VERSION = "authenticity_composition_v1"
_AUTHENTICITY_MIN_SAMPLE_FOR_FULL_CONFIDENCE = 20
_AUTHENTICITY_MAX_DESCONHECIDO_FLOOR_PCT = 30.0


def calibrate_authenticity_composition(raw_suspeito_pct, sample_n):
    """SPEC-005 §4.4: recebe o sinal bruto de "risco" (0-100, mesma escala de
    `estimate_fake_followers_risk`) e o decompõe em base_real/suspeito/
    desconhecido em vez de expor um único percentual de "risco" — evita que a
    heurística pareça uma acusação ("X% de audiência fraudulenta").

    Amostras pequenas (poucos comentários coletados) não sustentam uma
    leitura de suspeita alta: reservamos um piso de `desconhecido_pct`
    inversamente proporcional ao tamanho da amostra
    (`_AUTHENTICITY_MIN_SAMPLE_FOR_FULL_CONFIDENCE` comentários = piso zero,
    amostra vazia = piso máximo) e reduzimos `suspeito_pct` na mesma
    proporção — assim um único sinal isolado (ex.: pod_index alto com 1
    comentário coletado) nunca vira penalidade dominante (SPEC-005 §4.4 item
    4). `base_real_pct + suspeito_pct + desconhecido_pct == 100` sempre que a
    amostra é avaliável, por construção (base_real é o resto)."""
    cobertura_amostra = min(sample_n / _AUTHENTICITY_MIN_SAMPLE_FOR_FULL_CONFIDENCE, 1.0)
    desconhecido_pct = (1 - cobertura_amostra) * _AUTHENTICITY_MAX_DESCONHECIDO_FLOOR_PCT
    suspeito_pct = max(0.0, min(raw_suspeito_pct * cobertura_amostra, 100.0 - desconhecido_pct))
    base_real_pct = 100.0 - suspeito_pct - desconhecido_pct

    if sample_n <= 0:
        confidence = "baixa"
    elif sample_n < _AUTHENTICITY_MIN_SAMPLE_FOR_FULL_CONFIDENCE:
        confidence = "media"
    else:
        confidence = "alta"

    return {
        "base_real_pct": base_real_pct,
        "suspeito_pct": suspeito_pct,
        "desconhecido_pct": desconhecido_pct,
        "confidence": confidence,
        "sample_n": sample_n,
        "method_version": _AUTHENTICITY_METHOD_VERSION,
    }


def calc_audience_authenticity_signal(engagement_by_followers_metric, followers_count, pod_index_metric, sample_n=None):
    """audience_authenticity_signal (BENCHMARK-001.md §4.3/§7.2): sinal
    probabilístico composto (`is_estimated=True`) que reaproveita
    `estimate_fake_followers_risk` sobre o par (déficit de engajamento por
    seguidores, pod_index) já calculados no próprio audit_report. NÃO é um
    detector de seguidores falsos equivalente a ferramentas comerciais —
    a ressalva explícita disso vai sempre junto do valor. 'indisponivel'
    quando o pod_index de origem também está indisponível (amostra sem
    comentários), para não fabricar um sinal sem nenhum lastro na
    audiência.

    `sample_n` (SPEC-005 §4.4, opcional): quando informado (tamanho da
    amostra de comentários usada para calcular pod_index/engajamento), o
    resultado ganha a composição calibrada de `calibrate_authenticity_composition`
    (base_real_pct/suspeito_pct/desconhecido_pct/method_version), com
    `confidence` recalculada pela cobertura da amostra. Sem `sample_n`
    (chamada legada), o retorno mantém exatamente o formato anterior."""
    if pod_index_metric["value"] is None:
        return {
            "value": None,
            "unit": "percent",
            "kind": None,
            "source": "local_heuristic_v1",
            "confidence": None,
            "status": "indisponivel",
            "is_estimated": True,
            "method": None,
            "ressalvas": [
                "Sem comentários coletados na amostra — depende do pod_index, que "
                "também está indisponível."
            ],
        }

    pod_index_ratio = pod_index_metric["value"] / 100
    engagement_value = engagement_by_followers_metric["value"]
    engagement_ratio = (engagement_value / 100) if engagement_value is not None else 0.0

    estimate = estimate_fake_followers_risk(engagement_ratio, followers_count, pod_index_ratio)

    result = {
        "value": estimate["value"],
        "unit": "percent",
        "kind": "estimated",
        "source": "local_heuristic_v1",
        "confidence": estimate["confidence"],
        "status": "ok",
        "is_estimated": True,
        "method": estimate["method"],
        "ressalvas": [
            "Estimativa heurística local — NÃO é um detector de seguidores falsos "
            "equivalente a ferramentas comerciais (Modash/HypeAuditor); não deve "
            "ser lida como percentual definitivo de audiência inautêntica.",
            "'suspeito' não é fraude confirmada — é um sinal que pode exigir revisão "
            "humana antes de qualquer decisão.",
        ],
    }

    if sample_n is not None:
        composition = calibrate_authenticity_composition(estimate["value"], sample_n)
        result["base_real_pct"] = composition["base_real_pct"]
        result["suspeito_pct"] = composition["suspeito_pct"]
        result["desconhecido_pct"] = composition["desconhecido_pct"]
        result["sample_n"] = composition["sample_n"]
        result["method_version"] = composition["method_version"]
        result["confidence"] = composition["confidence"]

    return result


def extract_top_posts(posts, limit=3, followers_count=None):
    """top_posts (BENCHMARK-001.md §4.4/§4.5, ISSUE-001.md §5.9/§4.1): ranking
    dos posts da amostra por engajamento absoluto (likes + comments), com o
    engajamento relativo (sobre followers_count, quando informado) anexado a
    cada item. Não é uma estimativa — os posts retornados já estão na
    amostra coletada; 'indisponivel' só quando a amostra não tem nenhum
    post."""
    if not posts:
        return {
            "value": None,
            "unit": "count",
            "kind": None,
            "source": "local_scraper_sample",
            "confidence": None,
            "status": "indisponivel",
            "posts": [],
            "ressalvas": ["Sem posts na amostra — top posts indisponível."],
        }

    ranked = sorted(posts, key=_interactions, reverse=True)[:limit]

    items = []
    for post in ranked:
        raw = post.get("raw") or {}
        shortcode = raw.get("shortcode")
        absolute = _interactions(post)
        items.append(
            {
                "post_id": post.get("post_id"),
                "shortcode": shortcode,
                "link": f"https://www.instagram.com/p/{shortcode}/" if shortcode else None,
                "published_at": raw.get("published_at"),
                "media_type": raw.get("media_type"),
                "likes_count": post.get("likes_count") or 0,
                "comments_count": post.get("comments_count") or 0,
                "engagement_absolute": absolute,
                "engagement_rate": (absolute / followers_count * 100) if followers_count else None,
            }
        )

    return {
        "value": len(items),
        "unit": "count",
        "kind": "derived",
        "source": "local_scraper_sample",
        "confidence": "high",
        "status": "ok",
        "posts": items,
        "ressalvas": [],
    }


POPULAR_TAGS_MIN_COUNT = 2


def extract_popular_tags(posts, limit=10, min_count=POPULAR_TAGS_MIN_COUNT):
    """popular_tags (BENCHMARK-001.md §4.4, ISSUE-001.md §4.1): frequência de
    hashtags nas legendas já coletadas (post.raw.caption) — só regex local
    sobre texto já raspado, sem chamada externa. 'indisponivel' quando
    nenhuma legenda coletada contém hashtag.

    SPRINT-003 (feedback editorial): hashtag com 1 única ocorrência é ruído,
    não "popularidade" — min_count descarta tags sem recorrência real antes
    de listar; se nenhuma sobrar, cai no mesmo estado 'indisponivel' de
    "sem hashtag coletada", só com ressalva diferente."""
    counts = Counter()
    for post in posts:
        caption = (post.get("raw") or {}).get("caption") or ""
        for tag in _HASHTAG_PATTERN.findall(caption):
            counts[f"#{tag.lower()}"] += 1

    if not counts:
        return {
            "value": None,
            "unit": "count",
            "kind": None,
            "source": "local_scraper_sample",
            "confidence": None,
            "status": "indisponivel",
            "tags": [],
            "ressalvas": ["Nenhuma legenda coletada contém hashtag — tags populares indisponíveis."],
        }

    recorrentes = [(tag, count) for tag, count in counts.most_common() if count >= min_count]
    if not recorrentes:
        return {
            "value": None,
            "unit": "count",
            "kind": None,
            "source": "local_scraper_sample",
            "confidence": None,
            "status": "indisponivel",
            "tags": [],
            "ressalvas": [
                f"Nenhuma hashtag apareceu em {min_count}+ posts nesta amostra — só ocorrências "
                "isoladas, descartadas para evitar ruído."
            ],
        }

    items = [{"tag": tag, "count": count} for tag, count in recorrentes[:limit]]

    return {
        "value": len(items),
        "unit": "count",
        "kind": "derived",
        "source": "local_scraper_sample",
        "confidence": "high",
        "status": "ok",
        "tags": items,
        "ressalvas": [],
    }


def _post_has_sponsor_language(caption):
    return any(pattern.search(caption) for pattern in SPONSORED_PATTERNS.values())


def extract_brand_mentions(posts, limit=10):
    """brand_mentions (BENCHMARK-001.md §4.4/§4.5, ISSUE-001.md §4.5): conta
    menções a outros perfis/marcas (@handle) nas legendas já coletadas,
    separando menções orgânicas de publis confirmadas (RF-09). Uma menção
    isolada NÃO é prova de publicidade (ISSUE-001.md §4.5) — só é marcada
    'publi_confirmada' quando a mesma legenda também contém linguagem
    explícita de patrocínio (filters.SPONSORED_PATTERNS, o mesmo critério de
    filters.detect_sponsored_posts). 'indisponivel' quando nenhuma legenda
    coletada contém menção a outro perfil."""
    counts = defaultdict(lambda: {"count": 0, "confirmadas": 0, "organicas": 0})

    for post in posts:
        caption = (post.get("raw") or {}).get("caption") or ""
        if not caption:
            continue
        handles = BRAND_MENTION_PATTERN.findall(caption)
        if not handles:
            continue
        is_publi = _post_has_sponsor_language(caption)
        for handle in handles:
            key = handle.lower()
            counts[key]["count"] += 1
            if is_publi:
                counts[key]["confirmadas"] += 1
            else:
                counts[key]["organicas"] += 1

    if not counts:
        return {
            "value": None,
            "unit": "count",
            "kind": None,
            "source": "local_scraper_sample",
            "confidence": None,
            "status": "indisponivel",
            "mentions": [],
            "ressalvas": [
                "Nenhuma legenda coletada contém menção a outro perfil (@handle) — "
                "menções de marcas indisponíveis."
            ],
        }

    ranked = sorted(counts.items(), key=lambda item: item[1]["count"], reverse=True)[:limit]
    items = [
        {
            "handle": f"@{handle}",
            "count": data["count"],
            "confirmadas": data["confirmadas"],
            "organicas": data["organicas"],
            "tipo": "publi_confirmada" if data["confirmadas"] > 0 else "mencao_organica",
        }
        for handle, data in ranked
    ]

    return {
        "value": len(items),
        "unit": "count",
        "kind": "derived",
        "source": "local_scraper_sample",
        "confidence": "medium",
        "status": "ok",
        "mentions": items,
        "ressalvas": [
            "Menção não é prova suficiente de publicidade por si só (ISSUE-001.md §4.5) — "
            "'publi_confirmada' exige linguagem de patrocínio explícita na legenda, não "
            "apenas a marcação (@handle)."
        ],
    }


def calc_gender_distribution_metric(posts, names_db=None):
    """gender_distribution (BENCHMARK-001.md §4.4/§7.3, Sprint 002 Fase 4):
    envelope canônico em torno de demographics.summarize_gender_distribution
    sobre os comentários já coletados na amostra (post.raw.comments). 'value'
    é a cobertura em percentual (comentários com gênero identificado — F ou
    M — sobre o total da amostra); 'indisponivel' sem comentários
    coletados."""
    names_db = names_db if names_db is not None else demographics.DEFAULT_NAMES_DB
    comments = _extract_comments(posts)

    if not comments:
        return {
            "value": None,
            "unit": "percent",
            "kind": None,
            "source": "local_comment_sample",
            "confidence": None,
            "status": "indisponivel",
            "counts": {"feminino": 0, "masculino": 0, "indeterminado": 0},
            "percentuais": {"feminino": 0.0, "masculino": 0.0, "indeterminado": 0.0},
            "total_identificados": 0,
            "feminino_validado": 0,
            "masculino_validado": 0,
            "genero_validado_n": 0,
            "genero_unknown_n": 0,
            "feminino_pct": 0.0,
            "masculino_pct": 0.0,
            "coverage_gender": 0.0,
            "ressalvas": [
                "Sem comentários coletados na amostra — distribuição de gênero indisponível.",
                _DEMOGRAPHIC_SAMPLE_RESSALVA,
            ],
        }

    summary = demographics.summarize_gender_distribution(comments, names_db=names_db)
    # SPEC-005 §4.1: composição normalizada pela amostra reconhecida
    # (feminino_validado + masculino_validado), aditiva ao "percentuais"/
    # "cobertura" legados acima (mantidos intocados por compatibilidade).
    valid_composition = demographics.summarize_gender_distribution_valid(comments, names_db=names_db)

    return {
        "value": summary["cobertura"] * 100,
        "unit": "percent",
        "kind": "estimated",
        "source": "local_comment_sample_name_heuristic",
        "confidence": "medium",
        "status": "ok",
        "counts": summary["counts"],
        "percentuais": summary["percentuais"],
        "total_identificados": summary["total_identificados"],
        "feminino_validado": valid_composition["feminino_validado"],
        "masculino_validado": valid_composition["masculino_validado"],
        "genero_validado_n": valid_composition["genero_validado_n"],
        "genero_unknown_n": valid_composition["genero_unknown_n"],
        "feminino_pct": valid_composition["feminino_pct"],
        "masculino_pct": valid_composition["masculino_pct"],
        "coverage_gender": valid_composition["coverage_gender"],
        "ressalvas": [_DEMOGRAPHIC_SAMPLE_RESSALVA],
    }


def calc_region_distribution_metric(posts, ddd_to_uf=None):
    """region_distribution (BENCHMARK-001.md §4.4/§7.3, Sprint 002 Fase 4):
    mesmo padrão de envelope, em torno de
    demographics.summarize_region_distribution_with_coverage. 'value' é a
    cobertura em percentual (comentários com ao menos uma UF detectada sobre
    o total da amostra); 'indisponivel' sem comentários coletados."""
    ddd_to_uf = ddd_to_uf if ddd_to_uf is not None else demographics.DEFAULT_DDD_TO_UF
    comments = _extract_comments(posts)

    if not comments:
        return {
            "value": None,
            "unit": "percent",
            "kind": None,
            "source": "local_comment_sample",
            "confidence": None,
            "status": "indisponivel",
            "distribuicao": [],
            "ressalvas": [
                "Sem comentários coletados na amostra — distribuição de região indisponível.",
                _DEMOGRAPHIC_SAMPLE_RESSALVA,
            ],
        }

    summary = demographics.summarize_region_distribution_with_coverage(comments, ddd_to_uf=ddd_to_uf)

    return {
        "value": summary["cobertura"] * 100,
        "unit": "percent",
        "kind": "derived",
        "source": "local_comment_sample",
        "confidence": "medium",
        "status": "ok",
        "distribuicao": summary["distribuicao"],
        "ressalvas": [_DEMOGRAPHIC_SAMPLE_RESSALVA],
    }


def build_audit_report(posts, followers_count, names_db=None, ddd_to_uf=None):
    """Contrato canônico de auditoria (BENCHMARK-001.md §6/§7, ISSUE-001.md
    §6.2). Cada métrica em `metrics` já é autodescritiva (value/kind/source/
    confidence/ressalvas); `provenance` resume a origem de cada campo num
    formato tabular, para auditoria rápida sem percorrer o objeto inteiro.
    Sprint 002 Fase 3 acrescenta a decomposição de qualidade da audiência
    (pod_index/shallow_ratio/creator_response_rate/
    audience_authenticity_signal — BENCHMARK-001.md §4.3/§7.2) às 3 taxas de
    engajamento da Fase 1/2. Fase 4 acrescenta Top Posts/tags populares/
    menções de marca (BENCHMARK-001.md §4.4/§4.5, ISSUE-001.md §4.1/§4.5/
    §5.9) e demografia expandida com cobertura amostral (BENCHMARK-001.md
    §4.4/§7.3) — `names_db`/`ddd_to_uf` são injetáveis (mesmo padrão de
    `demographics.infer_gender`/`infer_region`) para o pipeline real usar a
    base IBGE completa carregada por `data_loaders`, com fallback para os
    conjuntos de exemplo de `demographics` quando não informados.
    Retrocompatível: não substitui nem altera `scoring.calc_engagement_rate`
    (consumido por `app.py`/`src/exporter.py` como
    `analysis["engagement_rate"]`) nem `analysis["antifraude"]`/
    `analysis["demografia"]`, é um contrato adicional."""
    engagement_by_followers = calc_engagement_rate_by_followers(posts, followers_count)
    pod_index_metric = calc_pod_index_metric(posts)
    sample_n = len(_extract_comments(posts))

    metrics_report = {
        "engagement_rate_by_followers": engagement_by_followers,
        "engagement_rate_by_reach": calc_engagement_rate_by_reach(posts),
        "engagement_rate_by_views": calc_engagement_rate_by_views(posts),
        "pod_index": pod_index_metric,
        "shallow_ratio": calc_shallow_ratio_metric(posts),
        "creator_response_rate": calc_creator_response_rate_metric(posts),
        "top_posts": extract_top_posts(posts, followers_count=followers_count),
        "popular_tags": extract_popular_tags(posts),
        "brand_mentions": extract_brand_mentions(posts),
        "gender_distribution": calc_gender_distribution_metric(posts, names_db=names_db),
        "region_distribution": calc_region_distribution_metric(posts, ddd_to_uf=ddd_to_uf),
        # SPEC-005 §4.3 (Sprint 004, ISSUE-0010): performance independente por
        # Reels/Carrossel/Estático.
        "format_metrics": calculate_format_metrics(posts, followers_count),
        "audience_authenticity_signal": calc_audience_authenticity_signal(
            engagement_by_followers, followers_count, pod_index_metric, sample_n=sample_n
        ),
    }

    provenance = [
        {
            "field": field,
            # .get() em vez de [] (SPEC-005/ISSUE-0010): format_metrics tem um
            # envelope aninhado por formato em vez de kind/source/confidence/
            # status no nível raiz — sem isso a linha travaria a construção do
            # audit_report inteiro com KeyError.
            "kind": metric.get("kind"),
            "source": metric.get("source"),
            "confidence": metric.get("confidence"),
            "status": metric.get("status"),
        }
        for field, metric in metrics_report.items()
    ]

    return {"metrics": metrics_report, "provenance": provenance}


_FORMAT_ORDER = ("reels", "carrossel", "estatico")
_MEDIA_TYPE_TO_FORMAT = {"REEL": "reels", "CAROUSEL": "carrossel", "IMAGE": "estatico"}


def _classify_post_format(post):
    """SPEC-005 §5: precedência media_type explícito -> is_video -> não
    classificável. `raw.media_type` já vem normalizado por src/scraper.py
    para REEL/CAROUSEL/IMAGE (BENCHMARK-001.md §4.2); quando ausente (schema
    legado/cache antigo), cai para `is_video=True` -> reels. Nunca força
    'estatico' por padrão (UNKNOWN não pode ser forçado para Estático) —
    retorna None e o post fica fora dos três formatos, contabilizado como
    'não classificado' pelo chamador."""
    raw = post.get("raw") or {}
    media_type = raw.get("media_type")
    formato = _MEDIA_TYPE_TO_FORMAT.get(media_type)
    if formato is not None:
        return formato
    if raw.get("is_video"):
        return "reels"
    return None


def calculate_format_metrics(posts, followers_count):
    """format_metrics (SPEC-005 §4.3/§5): agregação independente de likes
    médios, comentários médios e ER por formato (Reels/Carrossel/Estático),
    reaproveitando o mesmo conjunto de ações de
    `engagement_rate_by_followers` (likes + comments) — não é uma fórmula
    paralela. `ER_f = interactions_f / (followers_count * n_f) * 100`.

    Uma categoria sem posts (ou sem seguidores conhecidos) fica
    'indisponivel' com `engagement_rate=None` — nunca 0.0%, que pareceria um
    formato observado e ruim em vez de simplesmente ausente. Posts sem
    `media_type`/`is_video` suficiente para classificação não entram
    silenciosamente em nenhum card; ficam em `unclassified_post_count`.

    O envelope de nível raiz segue o mesmo contrato canônico das demais
    métricas de `build_audit_report` (value/unit/kind/source/confidence/
    status/ressalvas — BENCHMARK-001.md §6/§7), com `formats`/
    `unclassified_post_count`/`total_post_count` como campos adicionais
    específicos desta métrica."""
    buckets = {formato: [] for formato in _FORMAT_ORDER}
    unclassified = 0

    for post in posts:
        formato = _classify_post_format(post)
        if formato is None:
            unclassified += 1
            continue
        buckets[formato].append(post)

    formats = {}
    for formato in _FORMAT_ORDER:
        format_posts = buckets[formato]
        n_f = len(format_posts)

        if n_f == 0:
            formats[formato] = {
                "format": formato,
                "post_count": 0,
                "average_likes": None,
                "average_comments": None,
                "engagement_rate": None,
                "status": "indisponivel",
                "kind": "derived",
                "denominator": "followers_count * post_count",
                "source": "local_posts",
                "coverage": 0.0,
                "ressalvas": ["Sem posts classificados neste formato na amostra."],
            }
            continue

        total_likes = sum(post.get("likes_count") or 0 for post in format_posts)
        total_comments = sum(post.get("comments_count") or 0 for post in format_posts)

        if not followers_count or followers_count <= 0:
            formats[formato] = {
                "format": formato,
                "post_count": n_f,
                "average_likes": total_likes / n_f,
                "average_comments": total_comments / n_f,
                "engagement_rate": None,
                "status": "indisponivel",
                "kind": "derived",
                "denominator": "followers_count * post_count",
                "source": "local_posts",
                "coverage": (n_f / len(posts)) if posts else 0.0,
                "ressalvas": ["Seguidores desconhecidos/zero — ER por formato indisponível."],
            }
            continue

        interactions_f = total_likes + total_comments
        er_f = (interactions_f / (followers_count * n_f)) * 100

        formats[formato] = {
            "format": formato,
            "post_count": n_f,
            "average_likes": total_likes / n_f,
            "average_comments": total_comments / n_f,
            "engagement_rate": er_f,
            "status": "ok",
            "kind": "derived",
            "denominator": "followers_count * post_count",
            "source": "local_posts",
            "coverage": (n_f / len(posts)) if posts else 0.0,
            "ressalvas": [],
        }

    any_ok = any(item["status"] == "ok" for item in formats.values())
    classified_count = len(posts) - unclassified

    return {
        "value": classified_count if any_ok else None,
        "unit": "count",
        "kind": "derived" if any_ok else None,
        "source": "local_posts",
        "confidence": "high" if any_ok else None,
        "status": "ok" if any_ok else "indisponivel",
        "ressalvas": (
            []
            if any_ok
            else ["Sem posts com formato classificável e seguidores conhecidos — performance por formato indisponível."]
        ),
        "formats": formats,
        "unclassified_post_count": unclassified,
        "total_post_count": len(posts),
    }


def calc_average_engagement(posts):
    """
    posts: list[{"likes_count": int, "comments_count": int}]

    Curtidas médias e comentários médios por post (RF do catálogo P0 do
    benchmark — BENCHMARK-001.md §4.2). Guarda soma, quantidade de posts e
    média sem arredondar o valor persistido; posts vazio -> zeros, nunca
    lança exceção nem divide por zero.

    Retorna: {
        "average_likes": float,
        "average_comments": float,
        "total_likes": int,
        "total_comments": int,
        "post_count": int,
    }
    """
    post_count = len(posts)
    total_likes = sum(post.get("likes_count") or 0 for post in posts)
    total_comments = sum(post.get("comments_count") or 0 for post in posts)

    return {
        "average_likes": (total_likes / post_count) if post_count else 0.0,
        "average_comments": (total_comments / post_count) if post_count else 0.0,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "post_count": post_count,
    }


def estimate_fake_followers_risk(engagement_rate, followers_count, pod_index):
    """Estimativa LOCAL e heurística de risco de audiência inautêntica —
    NÃO é um detector de seguidores falsos equivalente a ferramentas
    comerciais (Modash/HypeAuditor). BENCHMARK-001.md §4.3/§7.2 exige que
    esse tipo de sinal seja exposto com método e confiança explícitos, nunca
    como um percentual definitivo de "seguidores falsos".

    Combina dois sinais que já são calculados localmente e têm lastro no
    catálogo do benchmark:
    - discrepância entre a taxa de engajamento observada e o benchmark
      esperado para o porte da conta (engajamento muito abaixo do esperado
      é um sinal clássico de audiência comprada/inflada);
    - pod_index (repetição de comentaristas entre posts).

    Retorna: {
        "value": float (0-100, "% estimado de risco de audiência inautêntica"),
        "method": str,
        "confidence": "baixa"|"media",
        "kind": "estimated",
    }
    """
    if followers_count and followers_count > 0:
        _, benchmark = get_influencer_tier(followers_count)
        deficit_engajamento = max(0.0, 1 - (engagement_rate / benchmark)) if benchmark else 0.0
    else:
        deficit_engajamento = 0.0

    risco = (0.6 * deficit_engajamento + 0.4 * pod_index) * 100

    return {
        "value": min(risco, 100.0),
        "method": "heuristica_local_v1: 60% déficit de ER vs. benchmark do porte + 40% pod_index",
        "confidence": "baixa",
        "kind": "estimated",
    }


def calc_pod_index(posts):
    """
    posts: list[{"post_id": str, "commenters": list[str]}]

    "Pod" é um indício de engajamento combinado/artificial: um grupo de contas que
    comenta sistematicamente nos mesmos posts de um mesmo perfil. Aqui um comentarista
    é considerado "repetidor" quando aparece em 2 ou mais posts DISTINTOS do perfil
    (comentar 2x no mesmo post não conta como repetição entre posts).

    Retorna: {
        "total_comentarios": int,
        "comentaristas_unicos": int,
        "pod_index": float,  # proporção de comentários feitos por repetidores
        "top_repetidores": dict,  # {username: total de comentários feitos}, count >= 2
    }
    """
    posts_por_usuario = defaultdict(set)
    comentarios_por_usuario = defaultdict(int)
    total_comentarios = 0

    for post in posts:
        post_id = post.get("post_id")
        commenters = post.get("commenters") or []
        total_comentarios += len(commenters)
        for username in commenters:
            posts_por_usuario[username].add(post_id)
            comentarios_por_usuario[username] += 1

    comentaristas_unicos = len(posts_por_usuario)

    repetidores = {
        username: comentarios_por_usuario[username]
        for username, post_ids in posts_por_usuario.items()
        if len(post_ids) >= 2
    }

    comentarios_de_repetidores = sum(repetidores.values())
    pod_index = comentarios_de_repetidores / total_comentarios if total_comentarios else 0.0

    top_repetidores = dict(
        sorted(repetidores.items(), key=lambda item: item[1], reverse=True)
    )

    return {
        "total_comentarios": total_comentarios,
        "comentaristas_unicos": comentaristas_unicos,
        "pod_index": pod_index,
        "top_repetidores": top_repetidores,
    }
