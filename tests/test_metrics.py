import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import metrics


def test_calc_pod_index_empty_list_returns_zeros():
    result = metrics.calc_pod_index([])

    assert result == {
        "total_comentarios": 0,
        "comentaristas_unicos": 0,
        "pod_index": 0.0,
        "top_repetidores": {},
    }


def test_calc_pod_index_posts_without_commenters_never_raises():
    posts = [{"post_id": "p1"}, {"post_id": "p2", "commenters": []}]

    result = metrics.calc_pod_index(posts)

    assert result == {
        "total_comentarios": 0,
        "comentaristas_unicos": 0,
        "pod_index": 0.0,
        "top_repetidores": {},
    }


def test_calc_pod_index_no_repeat_commenters_returns_zero_pod_index():
    posts = [
        {"post_id": "p1", "commenters": ["ana", "bruna"]},
        {"post_id": "p2", "commenters": ["carla"]},
    ]

    result = metrics.calc_pod_index(posts)

    assert result["total_comentarios"] == 3
    assert result["comentaristas_unicos"] == 3
    assert result["pod_index"] == 0.0
    assert result["top_repetidores"] == {}


def test_calc_pod_index_detects_repeated_commenter_across_posts():
    posts = [
        {"post_id": "p1", "commenters": ["ana", "bruna", "carla"]},
        {"post_id": "p2", "commenters": ["ana", "diana"]},
        {"post_id": "p3", "commenters": ["ana", "bruna"]},
    ]

    result = metrics.calc_pod_index(posts)

    assert result["total_comentarios"] == 7
    assert result["comentaristas_unicos"] == 4
    assert result["pod_index"] == (3 + 2) / 7
    assert result["top_repetidores"] == {"ana": 3, "bruna": 2}


def test_calc_pod_index_top_repetidores_sorted_desc_and_excludes_single_appearance():
    posts = [
        {"post_id": "p1", "commenters": ["ana", "bruna"]},
        {"post_id": "p2", "commenters": ["ana", "bruna", "carla"]},
        {"post_id": "p3", "commenters": ["ana"]},
        {"post_id": "p4", "commenters": ["diana"]},
    ]

    result = metrics.calc_pod_index(posts)

    assert list(result["top_repetidores"].items()) == [("ana", 3), ("bruna", 2)]
    assert "carla" not in result["top_repetidores"]


def test_calc_pod_index_same_commenter_appearing_only_once_is_not_a_repetidor():
    posts = [{"post_id": "p1", "commenters": ["ana", "ana"]}]

    result = metrics.calc_pod_index(posts)

    assert result["total_comentarios"] == 2
    assert result["comentaristas_unicos"] == 1
    assert result["pod_index"] == 0.0
    assert result["top_repetidores"] == {}


def test_calc_average_engagement_empty_posts_returns_zeros():
    result = metrics.calc_average_engagement([])

    assert result == {
        "average_likes": 0.0,
        "average_comments": 0.0,
        "total_likes": 0,
        "total_comments": 0,
        "post_count": 0,
    }


def test_calc_average_engagement_computes_mean_per_post():
    posts = [
        {"likes_count": 100, "comments_count": 10},
        {"likes_count": 200, "comments_count": 20},
    ]

    result = metrics.calc_average_engagement(posts)

    assert result["average_likes"] == 150.0
    assert result["average_comments"] == 15.0
    assert result["total_likes"] == 300
    assert result["total_comments"] == 30
    assert result["post_count"] == 2


def test_calc_average_engagement_treats_missing_counts_as_zero_without_raising():
    posts = [{"likes_count": None, "comments_count": None}, {"likes_count": 50, "comments_count": 5}]

    result = metrics.calc_average_engagement(posts)

    assert result["average_likes"] == 25.0
    assert result["average_comments"] == 2.5


def test_estimate_fake_followers_risk_healthy_profile_scores_low():
    # Engajamento igual ao benchmark do próprio porte (nano, 8%) e nenhum pod.
    result = metrics.estimate_fake_followers_risk(engagement_rate=0.08, followers_count=5000, pod_index=0.0)

    assert result["value"] == 0.0
    assert result["kind"] == "estimated"
    assert result["confidence"] == "baixa"


def test_estimate_fake_followers_risk_low_engagement_and_high_pod_scores_high():
    # Engajamento muito abaixo do benchmark do porte + metade dos comentários vindos de pod.
    result = metrics.estimate_fake_followers_risk(engagement_rate=0.0, followers_count=5000, pod_index=0.5)

    assert result["value"] == 80.0


def test_estimate_fake_followers_risk_without_followers_count_uses_only_pod_index():
    result = metrics.estimate_fake_followers_risk(engagement_rate=0.0, followers_count=0, pod_index=0.25)

    assert result["value"] == 10.0


def test_estimate_fake_followers_risk_never_exceeds_100():
    result = metrics.estimate_fake_followers_risk(engagement_rate=0.0, followers_count=5000, pod_index=1.0)

    assert result["value"] == 100.0
