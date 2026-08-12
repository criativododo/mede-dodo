ENGAGEMENT_RATE_WEIGHT = 0.40
QUALIFIED_RATIO_WEIGHT = 0.25
RESPONSE_RATE_WEIGHT = 0.20
POD_INDEX_WEIGHT = 0.15

# (nome, limite_superior_de_seguidores, engajamento_benchmark_do_porte).
# Contas maiores engajam uma fração menor da própria base — isso é o padrão
# de mercado, não indício de perfil fraco/fraudulento. Os benchmarks abaixo
# são uma heurística de engenharia (não uma tabela validada com dados reais
# de campanha) para normalizar a expectativa de engajamento por porte, em vez
# de comparar toda conta contra uma meta fixa de 100% de engajamento.
INFLUENCER_TIERS = [
    ("nano", 10_000, 0.08),
    ("micro", 100_000, 0.05),
    ("mid", 500_000, 0.035),
    ("macro", 1_000_000, 0.02),
    ("top_tier", float("inf"), 0.012),
]


def get_influencer_tier(followers_count):
    """Retorna (nome_do_porte, engajamento_benchmark) para followers_count."""
    for name, max_followers, benchmark in INFLUENCER_TIERS:
        if followers_count <= max_followers:
            return name, benchmark
    return INFLUENCER_TIERS[-1][0], INFLUENCER_TIERS[-1][2]


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


def calc_dodo_score(engagement_rate, qualified_ratio, response_rate, pod_index, followers_count=None):
    """
    Score DODÔ: heurística de engenharia (0.0-10.0), NÃO uma fórmula validada com dados
    reais de campanha. Pesos sujeitos a calibração futura — ver Notas de Implementação
    em docs/issues/ISSUE-0005.md.

    engagement_rate é clampado a no máximo 1.0 antes de ponderar (perfis pequenos/virais
    podem passar de 100% de engajamento e não devem estourar o score).
    pod_index alto é tratado como indício de fraude e penaliza o score (peso aplicado a
    1 - pod_index).

    followers_count (opcional): quando informado (>0), o componente de engajamento é
    normalizado contra o benchmark do porte da influenciadora (get_influencer_tier) em
    vez de comparado direto contra o teto de 100% — sem isso, contas macro/top-tier
    (que naturalmente engajam uma fração menor da base, mesmo com audiência real e
    saudável) levam penalidade severa injustificada nesse componente. Sem
    followers_count, mantém o comportamento legado (engagement_rate cru vs. 1.0).
    """
    engagement_rate_clamped = min(engagement_rate, 1.0)

    if followers_count is not None and followers_count > 0:
        _, benchmark = get_influencer_tier(followers_count)
        engagement_component = min(engagement_rate_clamped / benchmark, 1.0)
    else:
        engagement_component = engagement_rate_clamped

    weighted_sum = (
        engagement_component * ENGAGEMENT_RATE_WEIGHT
        + qualified_ratio * QUALIFIED_RATIO_WEIGHT
        + response_rate * RESPONSE_RATE_WEIGHT
        + (1 - pod_index) * POD_INDEX_WEIGHT
    )

    return weighted_sum * 10
