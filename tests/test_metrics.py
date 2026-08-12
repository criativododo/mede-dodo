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
