import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import database


def make_temp_db(tmp_path):
    return tmp_path / "cache_test.db"


def test_clear_profile_cache_removes_profile_and_posts(tmp_path):
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "1", "raw": {"caption": "oi"}, "likes_count": 1, "comments_count": 1}],
        bio="bio",
        followers_count=100,
        db_path=db_path,
    )

    database.clear_profile_cache("perfil_a", db_path=db_path)

    assert database.get_cached_data("perfil_a", window_days=None, db_path=db_path) is None


def test_clear_profile_cache_does_not_affect_other_profiles(tmp_path):
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "1", "raw": {}, "likes_count": 1, "comments_count": 1}],
        db_path=db_path,
    )
    database.save_profile_data(
        "perfil_b",
        posts=[{"post_id": "1", "raw": {}, "likes_count": 2, "comments_count": 2}],
        db_path=db_path,
    )

    database.clear_profile_cache("perfil_a", db_path=db_path)

    assert database.get_cached_data("perfil_a", window_days=None, db_path=db_path) is None
    assert database.get_cached_data("perfil_b", window_days=None, db_path=db_path) is not None


def test_clear_profile_cache_is_safe_for_username_with_no_cached_data(tmp_path):
    db_path = make_temp_db(tmp_path)

    database.clear_profile_cache("perfil_inexistente", db_path=db_path)

    assert database.get_cached_data("perfil_inexistente", window_days=None, db_path=db_path) is None


def test_get_cached_data_with_source_filter_ignores_cache_from_a_different_source(tmp_path):
    """Regressão: cache gravado em Modo Demonstração nunca pode ser servido
    para um pedido de análise real do mesmo username, e vice-versa."""
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "1", "raw": {}, "likes_count": 1, "comments_count": 1}],
        source="demo",
        db_path=db_path,
    )

    assert database.get_cached_data("perfil_a", window_days=None, source="demo", db_path=db_path) is not None
    assert database.get_cached_data("perfil_a", window_days=None, source="real", db_path=db_path) is None
    # Sem filtro de source (compatibilidade retroativa): continua servindo.
    assert database.get_cached_data("perfil_a", window_days=None, db_path=db_path) is not None


def test_get_cached_data_treats_legacy_row_without_source_as_cache_miss_for_explicit_source(tmp_path):
    """Regressão do bug real observado em produção: uma linha de cache gravada
    antes da coluna `source` existir (source=NULL) não pode ser confundida com
    dado real nem com dado de demonstração quando o chamador pede uma origem
    específica."""
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_legado",
        posts=[{"post_id": "1", "raw": {}, "likes_count": 1, "comments_count": 1}],
        db_path=db_path,  # source não informado -> grava NULL, como o cache pré-migração
    )

    assert database.get_cached_data("perfil_legado", window_days=None, source="real", db_path=db_path) is None
    assert database.get_cached_data("perfil_legado", window_days=None, source="demo", db_path=db_path) is None
    assert database.get_cached_data("perfil_legado", window_days=None, db_path=db_path) is not None


def test_save_audit_report_persists_and_is_returned_by_get_cached_data(tmp_path):
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "1", "raw": {}, "likes_count": 1, "comments_count": 1}],
        followers_count=1000,
        db_path=db_path,
    )
    audit_report = {
        "metrics": {
            "engagement_rate_by_followers": {
                "value": 8.25,
                "kind": "derived",
                "source": "local_scraper_sample",
                "confidence": "high",
                "status": "ok",
                "ressalvas": [],
            },
        },
        "provenance": [
            {"field": "engagement_rate_by_followers", "kind": "derived", "source": "local_scraper_sample",
             "confidence": "high", "status": "ok"},
        ],
    }

    database.save_audit_report("perfil_a", audit_report, db_path=db_path)

    cached = database.get_cached_data("perfil_a", window_days=None, db_path=db_path)
    assert cached["audit_report"] == audit_report


def test_get_cached_data_returns_none_audit_report_when_never_saved(tmp_path):
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "1", "raw": {}, "likes_count": 1, "comments_count": 1}],
        db_path=db_path,
    )

    cached = database.get_cached_data("perfil_a", window_days=None, db_path=db_path)

    assert cached["audit_report"] is None


def test_save_audit_report_does_not_affect_posts_cache(tmp_path):
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "1", "raw": {"caption": "oi"}, "likes_count": 5, "comments_count": 2}],
        db_path=db_path,
    )

    database.save_audit_report("perfil_a", {"metrics": {}, "provenance": []}, db_path=db_path)

    cached = database.get_cached_data("perfil_a", window_days=None, db_path=db_path)
    assert len(cached["posts"]) == 1
    assert cached["posts"][0]["post_id"] == "1"
    assert cached["posts"][0]["likes_count"] == 5


def test_save_audit_report_is_safe_when_profile_was_never_saved(tmp_path):
    db_path = make_temp_db(tmp_path)

    database.save_audit_report("perfil_inexistente", {"metrics": {}, "provenance": []}, db_path=db_path)

    assert database.get_cached_data("perfil_inexistente", window_days=None, db_path=db_path) is None


def test_save_profile_data_replaces_previous_posts_snapshot_instead_of_accumulating(tmp_path):
    """Regressão: sem isso, uma raspagem real feita depois de uma raspagem em
    Modo Demonstração (post_ids diferentes, sem colisão) apenas ACRESCENTA
    posts ao cache existente, misturando comentários fictícios e reais na
    mesma resposta de get_cached_data."""
    db_path = make_temp_db(tmp_path)
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "demo_1", "raw": {}, "likes_count": 1, "comments_count": 1}],
        source="demo",
        db_path=db_path,
    )
    database.save_profile_data(
        "perfil_a",
        posts=[{"post_id": "real_1", "raw": {}, "likes_count": 2, "comments_count": 2}],
        source="real",
        db_path=db_path,
    )

    cached = database.get_cached_data("perfil_a", window_days=None, source="real", db_path=db_path)

    assert [post["post_id"] for post in cached["posts"]] == ["real_1"]
