import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import database
from src import scraper


def make_temp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    database.init_db(db_path=tmp.name)
    return tmp.name


def test_cache_write_and_read_roundtrip():
    db_path = make_temp_db()
    try:
        database.save_profile_data(
            "perfil_teste",
            posts=[
                {"post_id": "1", "raw": {"legenda": "oi"}, "likes_count": 10, "comments_count": 2},
            ],
            bio="bio de teste",
            followers_count=1000,
            db_path=db_path,
        )
        cached = database.get_cached_data("perfil_teste", window_days=90, db_path=db_path)
        assert cached is not None
        assert cached["profile"]["username"] == "perfil_teste"
        assert cached["profile"]["followers_count"] == 1000
        assert len(cached["posts"]) == 1
        assert cached["posts"][0]["likes_count"] == 10
    finally:
        os.unlink(db_path)


def test_cache_miss_returns_none_when_username_never_collected():
    db_path = make_temp_db()
    try:
        cached = database.get_cached_data("perfil_inexistente", window_days=30, db_path=db_path)
        assert cached is None
    finally:
        os.unlink(db_path)


def test_throttle_sleeps_within_jitter_bounds():
    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    delay = scraper.throttle(min_seconds=2, max_seconds=5, sleep_fn=fake_sleep)

    assert sleep_calls == [delay]
    assert 2 <= delay <= 5


def test_scrape_profile_returns_cache_without_calling_fetch_fn():
    db_path = make_temp_db()
    try:
        database.save_profile_data(
            "perfil_cache",
            posts=[{"post_id": "1", "raw": {}, "likes_count": 5, "comments_count": 1}],
            bio="bio",
            followers_count=500,
            db_path=db_path,
        )

        def fetch_fn_should_not_be_called(username, cookies):
            raise AssertionError("fetch_fn não deveria ser chamado quando há cache válido")

        result = scraper.scrape_profile(
            "perfil_cache",
            window_days=90,
            fetch_fn=fetch_fn_should_not_be_called,
            db_path=db_path,
        )

        assert result["profile"]["username"] == "perfil_cache"
    finally:
        os.unlink(db_path)


def test_scrape_profile_calls_throttle_and_fetch_when_no_cache():
    db_path = make_temp_db()
    calls = {"throttle": 0, "fetch": 0}

    def fake_throttle():
        calls["throttle"] += 1

    def fake_fetch(username, cookies):
        calls["fetch"] += 1
        return {
            "bio": "nova bio",
            "followers_count": 2000,
            "posts": [{"post_id": "9", "raw": {}, "likes_count": 20, "comments_count": 3}],
        }

    try:
        result = scraper.scrape_profile(
            "perfil_novo",
            window_days=90,
            fetch_fn=fake_fetch,
            throttle_fn=fake_throttle,
            db_path=db_path,
        )

        assert calls["throttle"] == 1
        assert calls["fetch"] == 1
        assert result["profile"]["followers_count"] == 2000
        assert result["posts"][0]["likes_count"] == 20
    finally:
        os.unlink(db_path)


def test_scrape_profile_raises_without_fetch_fn_when_no_cache():
    db_path = make_temp_db()
    try:
        try:
            scraper.scrape_profile("perfil_sem_fetch", window_days=90, db_path=db_path)
            assert False, "esperava NotImplementedError"
        except NotImplementedError:
            pass
    finally:
        os.unlink(db_path)
