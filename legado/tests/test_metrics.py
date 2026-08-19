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
_CONTENT_AFFINITY_FIELDS = {"top_posts", "popular_tags", "brand_mentions"}
_DEMOGRAPHIC_FIELDS = {"gender_distribution", "region_distribution"}
# SPRINT-004 / ISSUE-0010 / SPEC-005 §4.3: performance por formato — mesmo
# envelope canônico (value/unit/kind/source/confidence/status/ressalvas),
# com "formats"/"unclassified_post_count"/"total_post_count" adicionais.
_FORMAT_FIELDS = {"format_metrics"}
_METRIC_BASELINE_KEYS = {"value", "unit", "kind", "source", "confidence", "status", "ressalvas"}


def test_build_audit_report_has_canonical_metrics_and_provenance_shape():
    posts = [{"likes_count": 100, "comments_count": 10}]

    report = metrics.build_audit_report(posts, followers_count=1000)

    assert set(report.keys()) == {"metrics", "provenance"}
    assert (
        set(report["metrics"].keys())
        == _ENGAGEMENT_RATE_FIELDS
        | _AUDIENCE_QUALITY_FIELDS
        | _CONTENT_AFFINITY_FIELDS
        | _DEMOGRAPHIC_FIELDS
        | _FORMAT_FIELDS
    )

    for field in _ENGAGEMENT_RATE_FIELDS:
        metric = report["metrics"][field]
        assert set(metric.keys()) == _METRIC_BASELINE_KEYS | {
            "denominator",
            "included_actions",
            "post_count",
        }

    for field in _AUDIENCE_QUALITY_FIELDS | _CONTENT_AFFINITY_FIELDS | _DEMOGRAPHIC_FIELDS | _FORMAT_FIELDS:
        metric = report["metrics"][field]
        assert _METRIC_BASELINE_KEYS <= set(metric.keys())

    assert len(report["provenance"]) == 13
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


# --- Sprint 002 Fase 4: extract_top_posts -----------------------------------


def test_extract_top_posts_empty_posts_returns_indisponivel():
    result = metrics.extract_top_posts([])

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["posts"] == []


def test_extract_top_posts_ranks_by_absolute_engagement_descending():
    posts = [
        {
            "post_id": "p1",
            "likes_count": 10,
            "comments_count": 1,
            "raw": {"shortcode": "aaa", "published_at": "2026-08-01T00:00:00+00:00", "media_type": "IMAGE"},
        },
        {
            "post_id": "p2",
            "likes_count": 500,
            "comments_count": 50,
            "raw": {"shortcode": "bbb", "published_at": "2026-08-02T00:00:00+00:00", "media_type": "REEL"},
        },
        {
            "post_id": "p3",
            "likes_count": 100,
            "comments_count": 10,
            "raw": {"shortcode": "ccc", "published_at": "2026-08-03T00:00:00+00:00", "media_type": "CAROUSEL"},
        },
    ]

    result = metrics.extract_top_posts(posts, limit=2, followers_count=1000)

    assert result["status"] == "ok"
    assert result["value"] == 2
    assert [item["post_id"] for item in result["posts"]] == ["p2", "p3"]
    assert result["posts"][0]["shortcode"] == "bbb"
    assert result["posts"][0]["link"] == "https://www.instagram.com/p/bbb/"
    assert result["posts"][0]["media_type"] == "REEL"
    assert result["posts"][0]["engagement_absolute"] == 550
    assert round(result["posts"][0]["engagement_rate"], 4) == 55.0


def test_extract_top_posts_engagement_rate_is_none_without_followers_count():
    posts = [{"post_id": "p1", "likes_count": 10, "comments_count": 1, "raw": {"shortcode": "aaa"}}]

    result = metrics.extract_top_posts(posts)

    assert result["posts"][0]["engagement_rate"] is None


def test_extract_top_posts_never_raises_on_missing_raw_or_counts():
    posts = [{"post_id": "p1"}]

    result = metrics.extract_top_posts(posts)

    assert result["status"] == "ok"
    assert result["posts"][0]["shortcode"] is None
    assert result["posts"][0]["link"] is None
    assert result["posts"][0]["likes_count"] == 0
    assert result["posts"][0]["comments_count"] == 0


# --- Sprint 002 Fase 4: extract_popular_tags --------------------------------


def test_extract_popular_tags_no_captions_returns_indisponivel():
    posts = [{"raw": {"caption": "sem hashtag aqui"}}, {"post_id": "p2"}]

    result = metrics.extract_popular_tags(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["tags"] == []


def test_extract_popular_tags_counts_frequency_case_insensitive_and_sorted_desc():
    posts = [
        {"raw": {"caption": "amei o look #moda #Verao2026"}},
        {"raw": {"caption": "#MODA demais, quero #verao2026 inteiro"}},
        {"raw": {"caption": "#moda sempre"}},
    ]

    result = metrics.extract_popular_tags(posts, limit=10)

    assert result["status"] == "ok"
    assert result["tags"][0] == {"tag": "#moda", "count": 3}
    assert result["tags"][1] == {"tag": "#verao2026", "count": 2}
    assert result["value"] == 2


def test_extract_popular_tags_respects_limit():
    posts = [{"raw": {"caption": "#a #b #c"}}]

    result = metrics.extract_popular_tags(posts, limit=2, min_count=1)

    assert len(result["tags"]) == 2


def test_extract_popular_tags_discards_single_occurrence_as_noise():
    """SPRINT-003 (feedback editorial): hashtag citada em 1 único post não é
    "popular" — piso padrão de 2 ocorrências descarta ruído antes de listar."""
    posts = [
        {"raw": {"caption": "#lookdodia #publi"}},
        {"raw": {"caption": "#lookdodia demais"}},
    ]

    result = metrics.extract_popular_tags(posts)

    assert result["status"] == "ok"
    assert result["tags"] == [{"tag": "#lookdodia", "count": 2}]


def test_extract_popular_tags_all_below_min_count_returns_indisponivel():
    posts = [{"raw": {"caption": "#a #b #c"}}]

    result = metrics.extract_popular_tags(posts)

    assert result["status"] == "indisponivel"
    assert result["tags"] == []
    assert result["ressalvas"]


# --- Sprint 002 Fase 4: extract_brand_mentions ------------------------------


def test_extract_brand_mentions_no_mentions_returns_indisponivel():
    posts = [{"raw": {"caption": "sem nenhuma marca aqui"}}]

    result = metrics.extract_brand_mentions(posts)

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert result["mentions"] == []


def test_extract_brand_mentions_separates_organic_from_confirmed_publi():
    posts = [
        {"raw": {"caption": "look de hoje com @marca_organica, amei"}},
        {"raw": {"caption": "publi paga: use o código com @marca_publi #publi"}},
    ]

    result = metrics.extract_brand_mentions(posts)

    by_handle = {item["handle"]: item for item in result["mentions"]}
    assert by_handle["@marca_organica"]["tipo"] == "mencao_organica"
    assert by_handle["@marca_organica"]["confirmadas"] == 0
    assert by_handle["@marca_organica"]["organicas"] == 1
    assert by_handle["@marca_publi"]["tipo"] == "publi_confirmada"
    assert by_handle["@marca_publi"]["confirmadas"] == 1
    assert "Menção não é prova suficiente" in result["ressalvas"][0]


def test_extract_brand_mentions_counts_repeated_mentions_across_posts():
    posts = [
        {"raw": {"caption": "com @marca_x"}},
        {"raw": {"caption": "de novo @marca_x por aqui"}},
    ]

    result = metrics.extract_brand_mentions(posts)

    assert result["mentions"][0]["handle"] == "@marca_x"
    assert result["mentions"][0]["count"] == 2


# --- Sprint 002 Fase 4: gender_distribution / region_distribution metrics --


_FASE4_NAMES_DB = {
    "maria": {"F": 950, "M": 5},
    "joao": {"F": 2, "M": 900},
}
_FASE4_DDD_TO_UF = {"11": "SP"}
_FASE4_REGION_KEYWORDS = {"sao paulo": "SP"}


def _post_with_comments(comments):
    return [{"post_id": "p1", "raw": {"comments": comments}}]


def test_calc_gender_distribution_metric_no_comments_returns_indisponivel():
    result = metrics.calc_gender_distribution_metric([])

    assert result["value"] is None
    assert result["status"] == "indisponivel"
    assert any("amostragem" in r for r in result["ressalvas"])


def test_calc_gender_distribution_metric_computes_coverage_and_ressalva():
    posts = _post_with_comments(
        [
            {"username": "maria_silva", "texto": "linda"},
            {"username": "joao_pedro", "texto": "top"},
            {"username": "xyz123", "texto": "oi"},
        ]
    )

    result = metrics.calc_gender_distribution_metric(posts, names_db=_FASE4_NAMES_DB)

    assert result["status"] == "ok"
    assert result["unit"] == "percent"
    assert result["counts"] == {"feminino": 1, "masculino": 1, "indeterminado": 1}
    assert result["total_identificados"] == 2
    assert round(result["value"], 4) == round((2 / 3) * 100, 4)
    assert any("amostragem" in r for r in result["ressalvas"])


def test_calc_region_distribution_metric_no_comments_returns_indisponivel():
    result = metrics.calc_region_distribution_metric([])

    assert result["value"] is None
    assert result["status"] == "indisponivel"


def test_calc_region_distribution_metric_computes_distribution_and_coverage():
    posts = _post_with_comments(
        [
            {"username": "u1", "texto": "moro em sao paulo"},
            {"username": "u2", "texto": "nada aqui"},
        ]
    )

    result = metrics.calc_region_distribution_metric(posts, ddd_to_uf=_FASE4_DDD_TO_UF)

    assert result["status"] == "ok"
    assert result["unit"] == "percent"
    assert result["distribuicao"] == [{"uf": "SP", "pct": 1.0}]
    assert result["value"] == 50.0


def test_build_audit_report_wires_gender_and_region_using_injected_dbs():
    posts = _post_with_comments([{"username": "maria_silva", "texto": "moro em sao paulo"}])

    report = metrics.build_audit_report(
        posts,
        followers_count=1000,
        names_db=_FASE4_NAMES_DB,
        ddd_to_uf=_FASE4_DDD_TO_UF,
    )

    assert report["metrics"]["gender_distribution"]["status"] == "ok"
    assert report["metrics"]["gender_distribution"]["counts"]["feminino"] == 1


# --- SPRINT-004 / ISSUE-0010 / SPEC-005: denominador de gênero normalizado --


def test_calc_gender_distribution_metric_exposes_valid_sample_composition():
    """SPEC-005 §4.1/§5.4: o envelope de gender_distribution passa a expor a
    composição normalizada pela amostra reconhecida, além do 'percentuais'
    legado (mantido intocado para não quebrar o contrato existente)."""
    posts = _post_with_comments(
        [
            {"username": "maria_silva", "texto": "linda"},
            {"username": "joao_pedro", "texto": "top"},
            {"username": "xyz123", "texto": "oi"},
        ]
    )

    result = metrics.calc_gender_distribution_metric(posts, names_db=_FASE4_NAMES_DB)

    assert result["feminino_validado"] == 1
    assert result["masculino_validado"] == 1
    assert result["genero_validado_n"] == 2
    assert result["genero_unknown_n"] == 1
    assert result["feminino_pct"] == 50.0
    assert result["masculino_pct"] == 50.0
    assert round(result["coverage_gender"], 4) == round(2 / 3, 4)
    # contrato legado preservado (SPRINT-002 Fase 4, ainda testado acima)
    assert result["percentuais"] == {
        "feminino": 1 / 3,
        "masculino": 1 / 3,
        "indeterminado": 1 / 3,
    }


def test_calc_gender_distribution_metric_no_comments_has_zeroed_valid_composition():
    result = metrics.calc_gender_distribution_metric([])

    assert result["status"] == "indisponivel"
    assert result["feminino_validado"] == 0
    assert result["masculino_validado"] == 0
    assert result["genero_validado_n"] == 0
    assert result["coverage_gender"] == 0.0


# --- SPRINT-004 / ISSUE-0010 / SPEC-005 §4.3: performance por formato -------


def _post(post_id, likes, comments, media_type=None, is_video=False):
    raw = {"is_video": is_video}
    if media_type is not None:
        raw["media_type"] = media_type
    return {"post_id": post_id, "likes_count": likes, "comments_count": comments, "raw": raw}


def test_calculate_format_metrics_aggregates_each_format_independently():
    posts = [
        _post("r1", 100, 10, media_type="REEL", is_video=True),
        _post("r2", 300, 30, media_type="REEL", is_video=True),
        _post("c1", 50, 5, media_type="CAROUSEL"),
        _post("i1", 20, 2, media_type="IMAGE"),
        _post("i2", 40, 4, media_type="IMAGE"),
    ]

    result = metrics.calculate_format_metrics(posts, followers_count=1000)

    reels = result["formats"]["reels"]
    assert reels["post_count"] == 2
    assert reels["average_likes"] == 200.0
    assert reels["average_comments"] == 20.0
    assert reels["status"] == "ok"
    assert reels["kind"] == "derived"
    assert reels["denominator"] == "followers_count * post_count"
    # ER_f = (likes+comments) somados / (followers_count * n_f) * 100
    assert round(reels["engagement_rate"], 4) == round(((100 + 10 + 300 + 30) / (1000 * 2)) * 100, 4)

    carrossel = result["formats"]["carrossel"]
    assert carrossel["post_count"] == 1
    assert carrossel["average_likes"] == 50.0

    estatico = result["formats"]["estatico"]
    assert estatico["post_count"] == 2
    assert estatico["average_likes"] == 30.0

    assert result["unclassified_post_count"] == 0
    assert result["total_post_count"] == 5


def test_calculate_format_metrics_category_without_posts_is_indisponivel_not_zero():
    posts = [_post("i1", 20, 2, media_type="IMAGE")]

    result = metrics.calculate_format_metrics(posts, followers_count=1000)

    reels = result["formats"]["reels"]
    assert reels["post_count"] == 0
    assert reels["status"] == "indisponivel"
    assert reels["engagement_rate"] is None
    assert reels["average_likes"] is None
    assert reels["ressalvas"] != []


def test_calculate_format_metrics_unclassified_post_not_silently_bucketed():
    """Post sem media_type reconhecível e sem is_video=True não pode cair em
    Estático por padrão (SPEC-005 §5: 'UNKNOWN não pode ser forçado para
    Estático')."""
    posts = [
        _post("unknown1", 10, 1, media_type=None, is_video=False),
        _post("i1", 20, 2, media_type="IMAGE"),
    ]

    result = metrics.calculate_format_metrics(posts, followers_count=1000)

    assert result["unclassified_post_count"] == 1
    assert result["formats"]["estatico"]["post_count"] == 1


def test_calculate_format_metrics_is_video_true_classifies_as_reels_without_media_type():
    posts = [_post("v1", 10, 1, media_type=None, is_video=True)]

    result = metrics.calculate_format_metrics(posts, followers_count=1000)

    assert result["formats"]["reels"]["post_count"] == 1


def test_calculate_format_metrics_no_followers_marks_all_formats_indisponivel():
    posts = [_post("i1", 20, 2, media_type="IMAGE")]

    result = metrics.calculate_format_metrics(posts, followers_count=0)

    assert result["formats"]["estatico"]["status"] == "indisponivel"
    assert result["formats"]["estatico"]["engagement_rate"] is None


# --- SPRINT-004 / ISSUE-0010 / SPEC-005 §4.4: autenticidade calibrada ------


def test_calibrate_authenticity_composition_percentages_always_sum_to_100():
    for raw_suspeito_pct in (0.0, 25.0, 60.0, 100.0):
        for sample_n in (0, 3, 20, 500):
            result = metrics.calibrate_authenticity_composition(raw_suspeito_pct, sample_n)
            total = result["base_real_pct"] + result["suspeito_pct"] + result["desconhecido_pct"]
            assert round(total, 6) == 100.0
            assert 0.0 <= result["base_real_pct"] <= 100.0
            assert 0.0 <= result["suspeito_pct"] <= 100.0
            assert 0.0 <= result["desconhecido_pct"] <= 100.0


def test_calibrate_authenticity_composition_small_sample_raises_desconhecido_floor():
    tiny_sample = metrics.calibrate_authenticity_composition(90.0, sample_n=1)
    full_sample = metrics.calibrate_authenticity_composition(90.0, sample_n=200)

    assert tiny_sample["desconhecido_pct"] > full_sample["desconhecido_pct"]


def test_calibrate_authenticity_composition_single_signal_does_not_dominate_with_small_sample():
    """Um único sinal bruto de 100% de 'suspeita' com amostra mínima não pode
    virar 100% de suspeito_pct — o piso de desconhecido/baixa confiança
    precisa reduzir o peso desse sinal isolado (SPEC-005 §4.4 item 4)."""
    result = metrics.calibrate_authenticity_composition(100.0, sample_n=1)

    assert result["suspeito_pct"] < 100.0
    assert result["confidence"] in ("baixa", "media")


def test_calibrate_authenticity_composition_exposes_method_version_and_sample_n():
    result = metrics.calibrate_authenticity_composition(10.0, sample_n=42)

    assert result["sample_n"] == 42
    assert result["method_version"]
    assert result["confidence"] in ("baixa", "media", "alta")


def test_calc_audience_authenticity_signal_exposes_composition_when_sample_n_provided():
    posts = [
        {"post_id": "p1", "raw": {"comments": [{"username": "ana"}, {"username": "bruna"}]}},
        {"post_id": "p2", "raw": {"comments": [{"username": "ana"}]}},
    ]
    pod_index_metric = metrics.calc_pod_index_metric(posts)
    engagement_metric = metrics.calc_engagement_rate_by_followers(
        [{"likes_count": 1, "comments_count": 0}], followers_count=5000
    )

    result = metrics.calc_audience_authenticity_signal(engagement_metric, 5000, pod_index_metric, sample_n=3)

    assert result["value"] is not None
    assert "base_real_pct" in result
    assert "suspeito_pct" in result
    assert "desconhecido_pct" in result
    assert result["sample_n"] == 3
    assert round(result["base_real_pct"] + result["suspeito_pct"] + result["desconhecido_pct"], 6) == 100.0


def test_calc_audience_authenticity_signal_without_sample_n_keeps_legacy_shape():
    """Chamada legada (3 argumentos posicionais, sem sample_n) continua
    funcionando exatamente como antes — nenhuma regressão para quem já usa
    esta função sem o parâmetro novo."""
    unavailable_pod_index = metrics.calc_pod_index_metric([{"post_id": "p1", "raw": {}}])
    unavailable_engagement = metrics.calc_engagement_rate_by_followers([], followers_count=0)

    result = metrics.calc_audience_authenticity_signal(unavailable_engagement, 0, unavailable_pod_index)

    assert result["value"] is None
    assert "base_real_pct" not in result


# --- SPRINT-004 / ISSUE-0010 / SPEC-005 §4.5: respostas em thread ----------


def test_calc_creator_response_rate_metric_exposes_root_comment_thread_fields():
    posts = [
        {
            "post_id": "p1",
            "raw": {
                "comments": [
                    {"texto": "oi", "respondido": True},
                    {"texto": "oi de novo", "respondido": False},
                ]
            },
        },
    ]

    result = metrics.calc_creator_response_rate_metric(posts)

    assert result["root_comments_evaluable"] == 2
    assert result["root_comments_with_creator_reply"] == 1
    assert result["reply_detection_method"]


def test_build_audit_report_wires_format_metrics_and_authenticity_composition():
    posts = [
        _post("r1", 100, 10, media_type="REEL", is_video=True),
        _post("i1", 20, 2, media_type="IMAGE"),
    ]
    for post in posts:
        post["raw"]["comments"] = [{"username": "ana", "texto": "top"}]

    report = metrics.build_audit_report(posts, followers_count=1000)

    assert "format_metrics" in report["metrics"]
    assert report["metrics"]["format_metrics"]["formats"]["reels"]["post_count"] == 1
    assert "base_real_pct" in report["metrics"]["audience_authenticity_signal"]
