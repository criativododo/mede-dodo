ENGAGEMENT_RATE_WEIGHT = 0.40
QUALIFIED_RATIO_WEIGHT = 0.25
RESPONSE_RATE_WEIGHT = 0.20
POD_INDEX_WEIGHT = 0.15


def calc_engagement_rate(posts, followers_count):
    """
    posts: list[{"likes_count": int, "comments_count": int}]
    Retorna a média de (likes_count + comments_count) / followers_count por post.
    followers_count <= 0 ou posts vazio -> 0.0 (nunca lança exceção).
    """
    if followers_count <= 0 or not posts:
        return 0.0

    ratios = [
        (post["likes_count"] + post["comments_count"]) / followers_count
        for post in posts
    ]
    return sum(ratios) / len(ratios)


def calc_dodo_score(engagement_rate, qualified_ratio, response_rate, pod_index):
    """
    Score DODÔ: heurística de engenharia (0.0-10.0), NÃO uma fórmula validada com dados
    reais de campanha. Pesos sujeitos a calibração futura — ver Notas de Implementação
    em docs/issues/ISSUE-0005.md.

    engagement_rate é clampado a no máximo 1.0 antes de ponderar (perfis pequenos/virais
    podem passar de 100% de engajamento e não devem estourar o score).
    pod_index alto é tratado como indício de fraude e penaliza o score (peso aplicado a
    1 - pod_index).
    """
    engagement_rate_clamped = min(engagement_rate, 1.0)

    weighted_sum = (
        engagement_rate_clamped * ENGAGEMENT_RATE_WEIGHT
        + qualified_ratio * QUALIFIED_RATIO_WEIGHT
        + response_rate * RESPONSE_RATE_WEIGHT
        + (1 - pod_index) * POD_INDEX_WEIGHT
    )

    return weighted_sum * 10
