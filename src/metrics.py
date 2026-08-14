from collections import defaultdict

from src.scoring import get_influencer_tier

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


def build_audit_report(posts, followers_count):
    """Contrato canônico de auditoria (BENCHMARK-001.md §6, ISSUE-001.md §6.2),
    restrito nesta primeira fase da Sprint 002 às 3 taxas de engajamento
    formais do benchmark. Cada métrica em `metrics` já é autodescritiva
    (value/kind/source/confidence/ressalvas); `provenance` resume a origem de
    cada campo num formato tabular, para auditoria rápida sem percorrer o
    objeto inteiro. Retrocompatível: não substitui nem altera
    `scoring.calc_engagement_rate` (consumido por `app.py`/`src/exporter.py`
    como `analysis["engagement_rate"]`), é um contrato adicional."""
    metrics_report = {
        "engagement_rate_by_followers": calc_engagement_rate_by_followers(posts, followers_count),
        "engagement_rate_by_reach": calc_engagement_rate_by_reach(posts),
        "engagement_rate_by_views": calc_engagement_rate_by_views(posts),
    }

    provenance = [
        {
            "field": field,
            "kind": metric["kind"],
            "source": metric["source"],
            "confidence": metric["confidence"],
            "status": metric["status"],
        }
        for field, metric in metrics_report.items()
    ]

    return {"metrics": metrics_report, "provenance": provenance}


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
