from collections import defaultdict

from src.scoring import get_influencer_tier


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
