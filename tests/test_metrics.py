"""Testes unitários da ISSUE-004 — núcleo Rodada 1 (ER Branding) e Rodadas 2/3
(tipologia/P1, P2, P3, BQI, CI, densidade de patrocínio, parecer editorial),
aprovadas pelo Dani em 2026-08-15 com base em BENCHMARK-METRICS-001.md §6-9.

`metrics.py` nunca classifica comentário bruto — recebe `comment_labels` já
resolvido pela ISSUE-005 (`ai_local.py`/`ai_gemini.py`). P2 (retenção visual)
depende de save_rate/share_rate/VTR/alcance_qualificado, que a coleta pública
via Instaloader não expõe — por isso os testes de P2/BQI usam fixtures
sintéticas com esses sinais já resolvidos; não há garantia de que a
orquestração real (`src/app.py`) consiga alimentá-los hoje.
"""

import copy

import pytest

from src.features.analise import metrics


# --- weighted_interactions -----------------------------------------------------------


def test_weighted_interactions_applies_approved_action_weights():
    post = {"comments": 1, "shares": 1, "saves": 1, "likes": 1}
    assert metrics.weighted_interactions(post) == 11  # 3+3+2+3


def test_weighted_interactions_missing_fields_default_to_zero():
    assert metrics.weighted_interactions({}) == 0


# --- format_factor -----------------------------------------------------------


def test_format_factor_carrossel_is_1_20():
    assert metrics.format_factor("carrossel") == 1.20


def test_format_factor_foto_is_1_00():
    assert metrics.format_factor("foto") == 1.00


def test_format_factor_reel_is_0_80():
    assert metrics.format_factor("reel") == 0.80


def test_format_factor_unknown_format_returns_none_never_implicit_weight():
    assert metrics.format_factor("story_highlight") is None
    assert metrics.format_factor(None) is None


# --- resolve_denominator -----------------------------------------------------------


def test_resolve_denominator_prefers_reach_unique_when_available():
    post = {"reach_unique": 1000}
    value, mode = metrics.resolve_denominator(post, followers_count=5000)
    assert (value, mode) == (1000, "reach_unique")


def test_resolve_denominator_falls_back_to_followers_when_reach_missing():
    post = {"reach_unique": None}
    value, mode = metrics.resolve_denominator(post, followers_count=5000)
    assert (value, mode) == (5000, "followers")


def test_resolve_denominator_unavailable_without_reach_or_followers():
    post = {"reach_unique": None}
    value, mode = metrics.resolve_denominator(post, followers_count=None)
    assert (value, mode) == (None, "unavailable")


def test_resolve_denominator_treats_zero_reach_as_absent_not_as_zero_division():
    post = {"reach_unique": 0}
    value, mode = metrics.resolve_denominator(post, followers_count=None)
    assert (value, mode) == (None, "unavailable")


def test_resolve_denominator_respects_reach_unique_only_preference():
    post = {"reach_unique": None}
    value, mode = metrics.resolve_denominator(post, followers_count=5000, allow_followers_fallback=False)
    assert (value, mode) == (None, "unavailable")


# --- calculate_er_branding -----------------------------------------------------------


def test_calculate_er_branding_uses_reach_unique_when_all_posts_have_reach():
    payload = {
        "profile": {"followers_count": 10000},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 2, "shares": 1, "saves": 1, "likes": 10},
            {"post_id": "p2", "format": "carrossel", "reach_unique": 2000, "comments": 0, "shares": 0, "saves": 5, "likes": 20},
        ],
    }
    result = metrics.calculate_er_branding(payload)
    assert result["denominator"] == "reach_unique"
    assert result["value"] == 3.68  # 100 * (1.00*41 + 1.20*70) / (1.00*1000 + 1.20*2000)
    assert result["posts_n"] == 2
    assert result["content_scope"] == "all_content_without_stories"
    assert result["format_weights"] == {"carrossel": 1.20, "foto": 1.00, "reel": 0.80}


def test_calculate_er_branding_falls_back_to_followers_when_reach_missing():
    payload = {
        "profile": {"followers_count": 10000},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": None, "comments": 1, "shares": 1, "saves": 1, "likes": 1},
        ],
    }
    result = metrics.calculate_er_branding(payload)
    assert result["denominator"] == "followers"
    assert result["value"] == 0.11  # 100 * 11 / 10000
    assert any("segu" in w for w in result["warnings"])


def test_calculate_er_branding_mixed_denominator_keeps_both_posts_and_warns():
    payload = {
        "profile": {"followers_count": 5000},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 1, "shares": 1, "saves": 1, "likes": 1},
            {"post_id": "p2", "format": "carrossel", "reach_unique": None, "comments": 1, "shares": 1, "saves": 1, "likes": 1},
        ],
    }
    result = metrics.calculate_er_branding(payload)
    assert result["denominator"] == "mixed"
    assert result["posts_n"] == 2  # nenhum post desaparece na mistura
    assert result["warnings"]


def test_calculate_er_branding_unavailable_denominator_never_returns_numeric_value():
    payload = {
        "profile": {},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": None, "comments": 1, "shares": 1, "saves": 1, "likes": 1},
        ],
    }
    result = metrics.calculate_er_branding(payload)
    assert result["value"] is None
    assert result["denominator"] == "unavailable"
    assert result["posts_excluded_no_denominator_n"] == 1
    assert result["warnings"]


def test_calculate_er_branding_zero_reach_never_produces_infinite_or_misleading_zero():
    payload = {
        "profile": {},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 0, "comments": 1, "shares": 1, "saves": 1, "likes": 1},
        ],
    }
    result = metrics.calculate_er_branding(payload)
    assert result["value"] is None
    assert result["denominator"] == "unavailable"


def test_calculate_er_branding_excludes_unknown_format_with_explicit_warning():
    payload = {
        "profile": {"followers_count": 10000},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 0, "shares": 0, "saves": 0, "likes": 100},
            {"post_id": "p2", "format": "highlight", "reach_unique": 500, "comments": 0, "shares": 0, "saves": 0, "likes": 999},
        ],
    }
    result = metrics.calculate_er_branding(payload)
    assert result["value"] == 30.0  # só p1 (1.00*300 / 1.00*1000); p2 nunca recebe peso implícito
    assert result["posts_n"] == 1
    assert result["posts_excluded_unknown_format_n"] == 1
    assert any("p2" in w for w in result["warnings"])


# --- calculate_er_by_format -----------------------------------------------------------


def test_calculate_er_by_format_returns_per_format_cuts():
    payload = {
        "profile": {},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 0, "shares": 0, "saves": 0, "likes": 100},
            {"post_id": "p2", "format": "foto", "reach_unique": 2000, "comments": 0, "shares": 0, "saves": 0, "likes": 200},
            {"post_id": "p3", "format": "carrossel", "reach_unique": 500, "comments": 0, "shares": 0, "saves": 0, "likes": 50},
        ],
    }
    result = metrics.calculate_er_by_format(payload)
    assert result["foto"] == {"value": 30.0, "posts_n": 2}
    assert result["carrossel"] == {"value": 30.0, "posts_n": 1}
    assert result["reel"] == {"value": None, "posts_n": 0}


# --- calculate_stories_context -----------------------------------------------------------


def test_calculate_stories_context_reports_count_as_separate_signal():
    payload = {"stories": [{"story_id": "s1"}, {"story_id": "s2"}, {"story_id": "s3"}]}
    assert metrics.calculate_stories_context(payload) == {
        "status": "separate_contextual_signal",
        "stories_n": 3,
    }


def test_stories_never_change_er_branding_value():
    base_payload = {
        "profile": {},
        "posts": [{"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 0, "shares": 0, "saves": 0, "likes": 100}],
    }
    with_stories = copy.deepcopy(base_payload)
    with_stories["stories"] = [{"story_id": "s1"}, {"story_id": "s2"}]

    value_without_stories = metrics.calculate_er_branding(base_payload)["value"]
    value_with_stories = metrics.calculate_er_branding(with_stories)["value"]

    assert value_without_stories == value_with_stories == 30.0


# --- calculate_metrics (orquestrador) -----------------------------------------------------------


def test_calculate_metrics_top_level_contract_and_pending_stubs():
    payload = {
        "profile": {"followers_count": 10000},
        "window": {"days": 90},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 2, "shares": 1, "saves": 1, "likes": 10},
        ],
        "stories": [],
    }
    result = metrics.calculate_metrics(payload)

    assert set(result.keys()) == {
        "status", "method_version", "er_branding", "er_by_format", "stories_context",
        "denominator_mode", "coverage", "provenance", "warnings",
        "comment_typology", "bqi", "ci", "sponsor_density", "editorial_opinion",
    }
    assert result["status"] == "ok"
    assert result["method_version"] == metrics.METHOD_VERSION
    assert result["denominator_mode"] == "reach_unique"
    # Sem comment_labels/p2_inputs/weekly_consistency no payload, Rodadas 2/3
    # retornam indisponivel explícito — nunca o stub literal antigo.
    assert result["comment_typology"]["status"] == "indisponivel"
    assert result["bqi"]["status"] == "indisponivel"
    assert result["ci"]["status"] == "indisponivel"
    assert result["sponsor_density"]["status"] == "ok"  # SD só depende de posts+is_sponsored, já presentes
    assert result["editorial_opinion"]["status"] == "indisponivel"


def test_calculate_metrics_no_posts_returns_insufficient_data():
    result = metrics.calculate_metrics({"profile": {}, "posts": []})
    assert result["status"] == "insufficient_data"
    assert result["er_branding"]["value"] is None


def test_calculate_metrics_is_deterministic_for_the_same_payload():
    payload = {
        "profile": {"followers_count": 10000},
        "posts": [
            {"post_id": "p1", "format": "reel", "reach_unique": 1500, "comments": 3, "shares": 2, "saves": 4, "likes": 40},
        ],
    }
    first = metrics.calculate_metrics(copy.deepcopy(payload))
    second = metrics.calculate_metrics(copy.deepcopy(payload))
    assert first == second


def test_calculate_metrics_coverage_reports_reach_unique_ratio():
    payload = {
        "profile": {"followers_count": 5000},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 0, "shares": 0, "saves": 0, "likes": 1},
            {"post_id": "p2", "format": "foto", "reach_unique": None, "comments": 0, "shares": 0, "saves": 0, "likes": 1},
        ],
    }
    coverage = metrics.calculate_metrics(payload)["coverage"]
    assert coverage["posts_total_n"] == 2
    assert coverage["posts_with_reach_unique_n"] == 1
    assert coverage["reach_unique_coverage_pct"] == 50.0
    assert coverage["posts_used_in_er_n"] == 2  # p2 sobrevive via fallback de seguidores


# --- calculate_comment_typology (Rodada 2 — V_AB e Pilar 1) -----------------------------------------------------------

def test_calculate_comment_typology_computes_v_ab_and_p1():
    result = metrics.calculate_comment_typology({"A": 10, "B": 20, "C": 5, "D": 15})
    assert result["status"] == "ok"
    assert result["v_ab"] == 60.0
    assert result["p1"] == pytest.approx(54.33, abs=0.01)
    assert result["counts"] == {"A": 10, "B": 20, "C": 5, "D": 15}


def test_calculate_comment_typology_empty_labels_is_indisponivel():
    result = metrics.calculate_comment_typology({})
    assert result["status"] == "indisponivel"
    assert result["v_ab"] is None
    assert result["p1"] is None


def test_calculate_comment_typology_zero_a_and_b_never_divides_by_zero():
    result = metrics.calculate_comment_typology({"A": 0, "B": 0, "C": 10, "D": 5})
    assert result["status"] == "ok"
    assert result["v_ab"] == 0.0
    assert result["p1"] == 0.0


# --- calculate_noise_reduction (Rodada 2 — Pilar 3) -----------------------------------------------------------

def test_calculate_noise_reduction_computes_p3():
    result = metrics.calculate_noise_reduction({"A": 10, "B": 20, "C": 5, "D": 15, "spam": 3})
    assert result["status"] == "ok"
    assert result["value"] == pytest.approx(77.2, abs=0.01)


def test_calculate_noise_reduction_empty_is_indisponivel():
    result = metrics.calculate_noise_reduction({})
    assert result["status"] == "indisponivel"
    assert result["value"] is None


# --- calculate_visual_retention (Rodada 2 — Pilar 2, requer sinais indisponíveis via scraping público) -----------------------------------------------------------

def test_calculate_visual_retention_computes_p2_when_all_rates_present():
    result = metrics.calculate_visual_retention(
        {"save_rate": 0.02, "share_rate": 0.01, "vtr": 0.25, "qualified_reach_rate": 0.70}
    )
    assert result["status"] == "ok"
    assert 0 <= result["value"] <= 100


def test_calculate_visual_retention_missing_any_rate_is_indisponivel():
    result = metrics.calculate_visual_retention({"save_rate": 0.02})
    assert result["status"] == "indisponivel"
    assert result["value"] is None


def test_calculate_visual_retention_out_of_band_rate_clips_to_0_or_100():
    result = metrics.calculate_visual_retention(
        {"save_rate": 10.0, "share_rate": 10.0, "vtr": 10.0, "qualified_reach_rate": 10.0}
    )
    assert result["value"] == 100.0


# --- calculate_bqi (Rodada 2 — combinação dos pilares) -----------------------------------------------------------

def test_calculate_bqi_combines_pillars_and_bands():
    result = metrics.calculate_bqi(p1=80, p2=60, p3=90)
    assert result["status"] == "ok"
    assert result["value"] == pytest.approx(69.5, abs=0.1)
    assert result["band"] == "saudavel"


def test_calculate_bqi_missing_p1_or_p2_is_indisponivel_never_zero():
    result = metrics.calculate_bqi(p1=None, p2=60, p3=90)
    assert result["status"] == "indisponivel"
    assert result["value"] is None


def test_calculate_bqi_missing_p3_defaults_to_no_penalty_but_warns():
    with_p3 = metrics.calculate_bqi(p1=80, p2=60, p3=100)
    without_p3 = metrics.calculate_bqi(p1=80, p2=60, p3=None)
    assert without_p3["status"] == "ok"
    assert without_p3["value"] == with_p3["value"]
    assert without_p3.get("warning")


def test_calculate_bqi_bands_match_benchmark_table():
    assert metrics.calculate_bqi(p1=100, p2=100, p3=100)["band"] == "excelente"
    assert metrics.calculate_bqi(p1=10, p2=10, p3=0)["band"] == "nao_recomendada"


# --- calculate_sponsor_density (Rodada 3 — SD, real hoje via is_sponsored) -----------------------------------------------------------

def test_calculate_sponsor_density_computes_ratio_over_comparable_posts():
    posts = [
        {"format": "foto", "is_sponsored": True},
        {"format": "foto", "is_sponsored": False},
        {"format": "reel", "is_sponsored": True},
        {"format": "highlight", "is_sponsored": True},  # formato desconhecido: nunca conta como comparável
    ]
    result = metrics.calculate_sponsor_density(posts)
    assert result["status"] == "ok"
    assert result["unidades_comparaveis_n"] == 3
    assert result["unidades_patrocinadas_n"] == 2
    assert result["value"] == pytest.approx(66.7, abs=0.1)
    assert result["band"] == "nao_recomendado"


def test_calculate_sponsor_density_no_comparable_posts_is_indisponivel():
    result = metrics.calculate_sponsor_density([])
    assert result["status"] == "indisponivel"
    assert result["value"] is None


# --- calculate_consistency (Rodada 3 — CI) -----------------------------------------------------------

def test_calculate_consistency_low_dispersion_and_high_floor_coverage_is_consistente():
    result = metrics.calculate_consistency(weekly_values=[5.0, 5.2, 4.8, 5.1, 5.0], floor=3.0)
    assert result["status"] == "ok"
    assert result["value"] >= 75
    assert result["band"] == "consistente"


def test_calculate_consistency_high_dispersion_and_low_floor_coverage_is_instavel():
    result = metrics.calculate_consistency(weekly_values=[1.0, 0.5, 20.0, 0.8, 0.3], floor=10.0)
    assert result["status"] == "ok"
    assert result["value"] < 60
    assert result["band"] == "instavel"


def test_calculate_consistency_without_floor_is_indisponivel():
    result = metrics.calculate_consistency(weekly_values=[5.0, 5.1, 5.2], floor=None)
    assert result["status"] == "indisponivel"
    assert result["value"] is None


def test_calculate_consistency_needs_at_least_two_weeks():
    result = metrics.calculate_consistency(weekly_values=[5.0], floor=3.0)
    assert result["status"] == "indisponivel"


# --- calculate_editorial_opinion (Rodada 3 — parecer combinado) -----------------------------------------------------------

def test_calculate_editorial_opinion_high_affinity():
    result = metrics.calculate_editorial_opinion(bqi=85, v_ab=45, ci=80, sd=15, d_pct=20)
    assert result["veredito"] == "recomendada_alta_afinidade"


def test_calculate_editorial_opinion_recommended_with_caveats():
    result = metrics.calculate_editorial_opinion(bqi=70, v_ab=35, ci=65, sd=22, d_pct=40)
    assert result["veredito"] == "recomendada_com_ressalvas"


def test_calculate_editorial_opinion_not_recommended_for_branding():
    result = metrics.calculate_editorial_opinion(bqi=55, v_ab=25, ci=55, sd=30, d_pct=40)
    assert result["veredito"] == "nao_recomendada_branding"


def test_calculate_editorial_opinion_viral_dependency_forces_not_recommended_for_branding():
    result = metrics.calculate_editorial_opinion(bqi=90, v_ab=45, ci=80, sd=10, d_pct=10, viral_dependency=True)
    assert result["veredito"] == "nao_recomendada_branding"


def test_calculate_editorial_opinion_blocker_always_wins_regardless_of_bqi():
    result = metrics.calculate_editorial_opinion(
        bqi=95, v_ab=50, ci=90, sd=5, d_pct=5, blockers={"fraude_provavel": True}
    )
    assert result["veredito"] == "nao_recomendada"


def test_calculate_editorial_opinion_missing_core_metric_is_indisponivel_never_fabricated():
    result = metrics.calculate_editorial_opinion(bqi=None, v_ab=45, ci=80, sd=15, d_pct=20)
    assert result["status"] == "indisponivel"
    assert result["veredito"] is None


# --- calculate_metrics com Rodadas 2/3 alimentadas (orquestrador completo) -----------------------------------------------------------

def test_calculate_metrics_wires_round_2_and_3_when_inputs_are_provided():
    payload = {
        "profile": {"followers_count": 10000},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 2, "shares": 1, "saves": 1, "likes": 10, "is_sponsored": False},
            {"post_id": "p2", "format": "carrossel", "reach_unique": 1200, "comments": 1, "shares": 0, "saves": 2, "likes": 20, "is_sponsored": True},
        ],
        "comment_labels": {"A": 10, "B": 20, "C": 5, "D": 15, "spam": 2},
        "p2_inputs": {"save_rate": 0.02, "share_rate": 0.01, "vtr": 0.25, "qualified_reach_rate": 0.70},
        "weekly_consistency": {"values": [5.0, 5.2, 4.8, 5.1, 5.0], "floor": 3.0},
    }
    result = metrics.calculate_metrics(payload)
    assert result["comment_typology"]["status"] == "ok"
    assert result["bqi"]["status"] == "ok"
    assert result["ci"]["status"] == "ok"
    assert result["sponsor_density"]["status"] == "ok"
    assert result["editorial_opinion"]["status"] == "ok"


def test_calculate_metrics_round_2_3_is_deterministic_for_the_same_payload():
    payload = {
        "profile": {"followers_count": 10000},
        "posts": [
            {"post_id": "p1", "format": "foto", "reach_unique": 1000, "comments": 2, "shares": 1, "saves": 1, "likes": 10, "is_sponsored": False},
        ],
        "comment_labels": {"A": 10, "B": 20, "C": 5, "D": 15, "spam": 2},
        "p2_inputs": {"save_rate": 0.02, "share_rate": 0.01, "vtr": 0.25, "qualified_reach_rate": 0.70},
    }
    first = metrics.calculate_metrics(copy.deepcopy(payload))
    second = metrics.calculate_metrics(copy.deepcopy(payload))
    assert first == second
