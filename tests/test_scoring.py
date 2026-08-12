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
