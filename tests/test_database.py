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
