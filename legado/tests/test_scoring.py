import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import scoring


def test_calc_engagement_rate_returns_zero_for_empty_posts():
    assert scoring.calc_engagement_rate([], 1000) == 0.0


def test_calc_engagement_rate_returns_zero_for_zero_followers():
    posts = [{"likes_count": 100, "comments_count": 10}]

    assert scoring.calc_engagement_rate(posts, 0) == 0.0


def test_calc_engagement_rate_returns_zero_for_negative_followers():
    posts = [{"likes_count": 100, "comments_count": 10}]

    assert scoring.calc_engagement_rate(posts, -50) == 0.0


def test_calc_engagement_rate_averages_ratio_per_post():
    posts = [
        {"likes_count": 100, "comments_count": 10},
        {"likes_count": 200, "comments_count": 20},
    ]

    result = scoring.calc_engagement_rate(posts, 1000)

    assert result == ((100 + 10) / 1000 + (200 + 20) / 1000) / 2


def test_calc_dodo_score_weights_all_components():
    score = scoring.calc_dodo_score(
        engagement_rate=0.5,
        qualified_ratio=0.8,
        response_rate=0.6,
        pod_index=0.2,
    )

    expected = (0.4 * 0.5 + 0.25 * 0.8 + 0.20 * 0.6 + 0.15 * (1 - 0.2)) * 10
    assert score == expected


def test_calc_dodo_score_clamps_engagement_rate_above_one():
    score = scoring.calc_dodo_score(
        engagement_rate=2.5,
        qualified_ratio=0.0,
        response_rate=0.0,
        pod_index=0.0,
    )

    expected = (0.4 * 1.0 + 0.25 * 0.0 + 0.20 * 0.0 + 0.15 * (1 - 0.0)) * 10
    assert score == expected


def test_calc_dodo_score_returns_max_for_ideal_profile():
    score = scoring.calc_dodo_score(
        engagement_rate=1.0,
        qualified_ratio=1.0,
        response_rate=1.0,
        pod_index=0.0,
    )

    assert score == 10.0


def test_calc_dodo_score_returns_min_for_worst_profile():
    score = scoring.calc_dodo_score(
        engagement_rate=0.0,
        qualified_ratio=0.0,
        response_rate=0.0,
        pod_index=1.0,
    )

    assert score == 0.0


def test_calc_dodo_score_high_pod_index_penalizes_score():
    low_pod_score = scoring.calc_dodo_score(
        engagement_rate=0.5,
        qualified_ratio=0.5,
        response_rate=0.5,
        pod_index=0.0,
    )
    high_pod_score = scoring.calc_dodo_score(
        engagement_rate=0.5,
        qualified_ratio=0.5,
        response_rate=0.5,
        pod_index=1.0,
    )

    assert high_pod_score < low_pod_score


def test_get_influencer_tier_classifies_by_followers_count():
    assert scoring.get_influencer_tier(5_000)[0] == "nano"
    assert scoring.get_influencer_tier(50_000)[0] == "micro"
    assert scoring.get_influencer_tier(300_000)[0] == "mid"
    assert scoring.get_influencer_tier(800_000)[0] == "macro"
    assert scoring.get_influencer_tier(5_000_000)[0] == "top_tier"


def test_get_influencer_tier_returns_lower_benchmark_for_bigger_tiers():
    """Porte maior -> meta de engajamento (%) esperada menor — contas grandes
    naturalmente engajam uma fração menor da base, isso é normal, não fraude."""
    _, nano_benchmark = scoring.get_influencer_tier(5_000)
    _, macro_benchmark = scoring.get_influencer_tier(800_000)
    _, top_tier_benchmark = scoring.get_influencer_tier(5_000_000)

    assert nano_benchmark > macro_benchmark > top_tier_benchmark


def test_calc_dodo_score_without_followers_count_keeps_legacy_absolute_engagement_behavior():
    """Compatibilidade: sem followers_count, o score deve continuar idêntico
    à fórmula original (engagement_rate cru contra teto de 1.0)."""
    score = scoring.calc_dodo_score(
        engagement_rate=0.5, qualified_ratio=0.8, response_rate=0.6, pod_index=0.2
    )
    expected = (0.4 * 0.5 + 0.25 * 0.8 + 0.20 * 0.6 + 0.15 * (1 - 0.2)) * 10
    assert score == expected


def test_calc_dodo_score_does_not_unjustly_penalize_macro_profile_with_real_high_engagement():
    """RF: perfis macro/top-tier com engajamento real alto para o próprio
    porte não devem levar penalidade severa injustificada só por terem uma
    taxa de engajamento absoluta menor que a de uma conta pequena."""
    macro_engagement_rate = 0.025  # 2.5%: ótimo para porte macro, péssimo perto de 100%
    without_tier_score = scoring.calc_dodo_score(
        engagement_rate=macro_engagement_rate, qualified_ratio=0.5, response_rate=0.5, pod_index=0.1
    )
    macro_score = scoring.calc_dodo_score(
        engagement_rate=macro_engagement_rate,
        qualified_ratio=0.5,
        response_rate=0.5,
        pod_index=0.1,
        followers_count=800_000,
    )

    assert macro_score > without_tier_score


def test_calc_dodo_score_caps_normalized_engagement_component_even_when_far_above_tier_benchmark():
    score_at_benchmark = scoring.calc_dodo_score(
        engagement_rate=0.02, qualified_ratio=0.0, response_rate=0.0, pod_index=0.0, followers_count=800_000
    )
    score_far_above_benchmark = scoring.calc_dodo_score(
        engagement_rate=0.5, qualified_ratio=0.0, response_rate=0.0, pod_index=0.0, followers_count=800_000
    )

    assert score_at_benchmark == score_far_above_benchmark


def test_calc_dodo_score_profiles_at_their_own_tier_benchmark_score_equally():
    """Um perfil nano no benchmark do próprio porte e um top-tier no benchmark
    do próprio porte devem pontuar igual no componente de engajamento — ambos
    estão 'na média esperada para o tamanho deles'."""
    _, nano_benchmark = scoring.get_influencer_tier(5_000)
    _, top_tier_benchmark = scoring.get_influencer_tier(5_000_000)

    nano_score = scoring.calc_dodo_score(
        engagement_rate=nano_benchmark, qualified_ratio=0.0, response_rate=0.0, pod_index=0.0, followers_count=5_000
    )
    top_tier_score = scoring.calc_dodo_score(
        engagement_rate=top_tier_benchmark,
        qualified_ratio=0.0,
        response_rate=0.0,
        pod_index=0.0,
        followers_count=5_000_000,
    )

    assert nano_score == top_tier_score
