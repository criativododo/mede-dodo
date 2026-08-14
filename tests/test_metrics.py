import json
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


# --- Decomposição de sinais de autenticidade da audiência (Sprint 002 Fase 3,
# BENCHMARK-001.md §4.3/§7.2) ---


def test_classify_pod_risk_below_10_percent_is_baixo():
    assert metrics.classify_pod_risk(0.0) == "baixo"
    assert metrics.classify_pod_risk(9.9) == "baixo"


def test_classify_pod_risk_between_10_and_25_percent_is_medio():
    assert metrics.classify_pod_risk(10.0) == "medio"
    assert metrics.classify_pod_risk(25.0) == "medio"


def test_classify_pod_risk_above_25_percent_is_alto():
    assert metrics.classify_pod_risk(25.1) == "alto"
    assert metrics.classify_pod_risk(100.0) == "alto"


def test_calc_pod_index_metric_no_comments_returns_unavailable():
    posts = [{"post_id": "p1", "raw": {}}]

    result = metrics.calc_pod_index_metric(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["kind"] is None
    assert result["top_repetidores"] == {}
    assert result["risk"] is None
    assert result["ressalvas"] != []


def test_calc_pod_index_metric_computes_percent_value_and_risk():
    posts = [
        {"post_id": "p1", "raw": {"comments": [{"username": "ana"}, {"username": "bruna"}]}},
        {"post_id": "p2", "raw": {"comments": [{"username": "ana"}]}},
    ]

    result = metrics.calc_pod_index_metric(posts)

    assert result["value"] == (2 / 3) * 100
    assert result["unit"] == "percent"
    assert result["kind"] == "derived"
    assert result["status"] == "ok"
    assert result["top_repetidores"] == {"ana": 2}
    assert result["risk"] == "alto"


def test_calc_shallow_ratio_metric_no_comments_returns_unavailable():
    posts = [{"post_id": "p1", "raw": {}}]

    result = metrics.calc_shallow_ratio_metric(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["shallow_count"] == 0
    assert result["total_count"] == 0


def test_calc_shallow_ratio_metric_computes_percent_of_shallow_comments():
    posts = [
        {
            "post_id": "p1",
            "raw": {
                "comments": [
                    {"texto": "linda"},
                    {"texto": "Qual o preço desse vestido?"},
                    {"texto": "gata"},
                    {"texto": "Tem no tamanho M?"},
                ]
            },
        },
    ]

    result = metrics.calc_shallow_ratio_metric(posts)

    assert result["value"] == 50.0
    assert result["unit"] == "percent"
    assert result["kind"] == "derived"
    assert result["status"] == "ok"
    assert result["shallow_count"] == 2
    assert result["total_count"] == 4


def test_calc_creator_response_rate_metric_no_comments_returns_unavailable():
    posts = [{"post_id": "p1", "raw": {}}]

    result = metrics.calc_creator_response_rate_metric(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["responded_count"] == 0
    assert result["total_count"] == 0


def test_calc_creator_response_rate_metric_computes_percent_of_responded_comments():
    posts = [
        {
            "post_id": "p1",
            "raw": {
                "comments": [
                    {"texto": "oi", "respondido": True},
                    {"texto": "oi de novo", "respondido": False},
                    {"texto": "ola", "respondido": True},
                    {"texto": "e ai", "respondido": False},
                ]
            },
        },
    ]

    result = metrics.calc_creator_response_rate_metric(posts)

    assert result["value"] == 50.0
    assert result["status"] == "ok"
    assert result["responded_count"] == 2
    assert result["total_count"] == 4


def test_calc_audience_authenticity_signal_unavailable_when_pod_index_metric_is_unavailable():
    unavailable_pod_index = metrics.calc_pod_index_metric([{"post_id": "p1", "raw": {}}])
    unavailable_engagement = metrics.calc_engagement_rate_by_followers([], followers_count=0)

    result = metrics.calc_audience_authenticity_signal(unavailable_engagement, 0, unavailable_pod_index)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["kind"] is None
    assert result["is_estimated"] is True
    assert result["ressalvas"] != []


def test_calc_audience_authenticity_signal_is_estimated_with_explicit_caveat():
    posts = [
        {"post_id": "p1", "raw": {"comments": [{"username": "ana"}, {"username": "bruna"}]}},
        {"post_id": "p2", "raw": {"comments": [{"username": "ana"}]}},
    ]
    pod_index_metric = metrics.calc_pod_index_metric(posts)
    engagement_metric = metrics.calc_engagement_rate_by_followers(
        [{"likes_count": 1, "comments_count": 0}], followers_count=5000
    )

    result = metrics.calc_audience_authenticity_signal(engagement_metric, 5000, pod_index_metric)

    assert result["value"] is not None
    assert 0.0 <= result["value"] <= 100.0
    assert result["kind"] == "estimated"
    assert result["is_estimated"] is True
    assert result["confidence"] == "baixa"
    assert result["ressalvas"] != []


# --- Contrato canônico de métricas e proveniência (Sprint 002, BENCHMARK-001.md §6/§7,
# ISSUE-001.md §5.3/§5.4/§6.2) ---


def test_calc_engagement_rate_by_followers_computes_mean_of_per_post_ratio_as_percent():
    posts = [
        {"likes_count": 100, "comments_count": 10},
        {"likes_count": 50, "comments_count": 5},
    ]

    result = metrics.calc_engagement_rate_by_followers(posts, followers_count=1000)

    assert result["value"] == 8.25
    assert result["unit"] == "percent"
    assert result["kind"] == "derived"
    assert result["source"] == "local_scraper_sample"
    assert result["confidence"] == "high"
    assert result["denominator"] == "followers_count"
    assert result["included_actions"] == ["likes", "comments"]
    assert result["post_count"] == 2
    assert result["status"] == "ok"
    assert result["ressalvas"] == []


def test_calc_engagement_rate_by_followers_empty_posts_returns_none_not_zero():
    result = metrics.calc_engagement_rate_by_followers([], followers_count=1000)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["kind"] is None
    assert result["confidence"] is None
    assert result["post_count"] == 0
    assert result["ressalvas"] != []


def test_calc_engagement_rate_by_followers_zero_followers_returns_none_without_raising():
    posts = [{"likes_count": 100, "comments_count": 10}]

    result = metrics.calc_engagement_rate_by_followers(posts, followers_count=0)

    assert result["value"] is None
    assert result["status"] == "indisponivel"


def test_calc_engagement_rate_by_followers_missing_counts_treated_as_zero_without_raising():
    posts = [{"likes_count": None, "comments_count": None}]

    result = metrics.calc_engagement_rate_by_followers(posts, followers_count=1000)

    assert result["value"] == 0.0
    assert result["status"] == "ok"


def test_calc_engagement_rate_by_reach_computes_total_interactions_over_total_reach():
    posts = [
        {"likes_count": 100, "comments_count": 10, "estimated_reach": 2000},
        {"likes_count": 50, "comments_count": 5, "estimated_reach": 1000},
    ]

    result = metrics.calc_engagement_rate_by_reach(posts)

    assert result["value"] == 5.5
    assert result["unit"] == "percent"
    assert result["kind"] == "derived"
    assert result["source"] == "post_level_estimated_reach"
    assert result["denominator"] == "estimated_reach"
    assert result["included_actions"] == ["likes", "comments"]
    assert result["post_count"] == 2
    assert result["status"] == "ok"


def test_calc_engagement_rate_by_reach_returns_none_when_no_post_has_reach_data():
    posts = [{"likes_count": 100, "comments_count": 10}]

    result = metrics.calc_engagement_rate_by_reach(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["ressalvas"] != []


def test_calc_engagement_rate_by_reach_empty_posts_never_raises():
    result = metrics.calc_engagement_rate_by_reach([])

    assert result["value"] is None
    assert result["status"] == "indisponivel"


def test_calc_engagement_rate_by_reach_ignores_posts_without_reach_but_uses_the_ones_with_it():
    posts = [
        {"likes_count": 100, "comments_count": 10, "estimated_reach": 2000},
        {"likes_count": 999, "comments_count": 999},
    ]

    result = metrics.calc_engagement_rate_by_reach(posts)

    assert result["value"] == 5.5
    assert result["post_count"] == 1


def test_calc_engagement_rate_by_views_computes_total_interactions_over_total_views_for_reels():
    posts = [
        {"likes_count": 100, "comments_count": 10, "raw": {"is_video": True, "video_view_count": 5000}},
        {"likes_count": 50, "comments_count": 5, "raw": {"is_video": True, "video_view_count": 2000}},
        {"likes_count": 30, "comments_count": 3, "raw": {"is_video": False, "video_view_count": None}},
    ]

    result = metrics.calc_engagement_rate_by_views(posts)

    assert result["value"] == (165 / 7000) * 100
    assert result["kind"] == "derived"
    assert result["source"] == "post_level_video_view_count"
    assert result["denominator"] == "video_view_count"
    assert result["post_count"] == 2
    assert result["status"] == "ok"


def test_calc_engagement_rate_by_views_returns_none_when_no_video_in_sample():
    posts = [{"likes_count": 100, "comments_count": 10, "raw": {"is_video": False}}]

    result = metrics.calc_engagement_rate_by_views(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"


def test_calc_engagement_rate_by_views_returns_none_when_video_has_no_view_count():
    posts = [{"likes_count": 100, "comments_count": 10, "raw": {"is_video": True, "video_view_count": None}}]

    result = metrics.calc_engagement_rate_by_views(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"


def test_calc_engagement_rate_by_views_returns_none_when_post_has_no_raw_dict():
    posts = [{"likes_count": 100, "comments_count": 10}]

    result = metrics.calc_engagement_rate_by_views(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"


def test_calc_engagement_rate_by_views_empty_posts_never_raises():
    result = metrics.calc_engagement_rate_by_views([])

    assert result["value"] is None
    assert result["status"] == "indisponivel"


_ENGAGEMENT_RATE_FIELDS = {
    "engagement_rate_by_followers",
    "engagement_rate_by_reach",
    "engagement_rate_by_views",
}
_AUDIENCE_QUALITY_FIELDS = {
    "pod_index",
    "shallow_ratio",
    "creator_response_rate",
    "audience_authenticity_signal",
}
_METRIC_BASELINE_KEYS = {"value", "unit", "kind", "source", "confidence", "status", "ressalvas"}


def test_build_audit_report_has_canonical_metrics_and_provenance_shape():
    posts = [{"likes_count": 100, "comments_count": 10}]

    report = metrics.build_audit_report(posts, followers_count=1000)

    assert set(report.keys()) == {"metrics", "provenance"}
    assert set(report["metrics"].keys()) == _ENGAGEMENT_RATE_FIELDS | _AUDIENCE_QUALITY_FIELDS

    for field in _ENGAGEMENT_RATE_FIELDS:
        metric = report["metrics"][field]
        assert set(metric.keys()) == _METRIC_BASELINE_KEYS | {
            "denominator",
            "included_actions",
            "post_count",
        }

    for field in _AUDIENCE_QUALITY_FIELDS:
        metric = report["metrics"][field]
        assert _METRIC_BASELINE_KEYS <= set(metric.keys())

    assert len(report["provenance"]) == 7
    for entry in report["provenance"]:
        assert set(entry.keys()) == {"field", "kind", "source", "confidence", "status"}
        assert entry["field"] in report["metrics"]
        assert entry["kind"] == report["metrics"][entry["field"]]["kind"]
        assert entry["source"] == report["metrics"][entry["field"]]["source"]


def test_build_audit_report_is_json_serializable():
    posts = [{"likes_count": 100, "comments_count": 10}]

    report = metrics.build_audit_report(posts, followers_count=1000)

    json.dumps(report)  # não deve lançar exceção


def test_build_audit_report_never_raises_on_empty_sample():
    report = metrics.build_audit_report([], followers_count=0)

    for metric in report["metrics"].values():
        assert metric["value"] is None
        assert metric["status"] == "indisponivel"


def test_build_audit_report_computes_reach_and_views_when_data_is_present():
    posts = [
        {
            "likes_count": 100,
            "comments_count": 10,
            "estimated_reach": 2000,
            "raw": {"is_video": True, "video_view_count": 5000},
        },
    ]

    report = metrics.build_audit_report(posts, followers_count=1000)

    assert report["metrics"]["engagement_rate_by_followers"]["status"] == "ok"
    assert report["metrics"]["engagement_rate_by_reach"]["status"] == "ok"
    assert report["metrics"]["engagement_rate_by_views"]["status"] == "ok"
