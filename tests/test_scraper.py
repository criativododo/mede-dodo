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


def test_get_cached_data_with_window_days_none_ignores_cutoff():
    db_path = make_temp_db()
    try:
        database.save_profile_data(
            "perfil_qualquer_idade",
            posts=[],
            bio="bio",
            followers_count=1,
            db_path=db_path,
        )

        cached = database.get_cached_data("perfil_qualquer_idade", window_days=None, db_path=db_path)

        assert cached is not None
        assert cached["profile"]["username"] == "perfil_qualquer_idade"
    finally:
        os.unlink(db_path)


def test_scrape_profile_falls_back_to_cache_when_fetch_fails_and_cache_exists():
    db_path = make_temp_db()
    try:
        database.save_profile_data(
            "perfil_fallback",
            posts=[{"post_id": "1", "raw": {}, "likes_count": 5, "comments_count": 1}],
            bio="bio antiga",
            followers_count=300,
            db_path=db_path,
        )

        def fetch_fn_network_error(username, cookies):
            raise ConnectionError("instagram bloqueou a coleta")

        # window_days=0 força o cache existente (salvo um instante atrás) a ficar
        # fora da janela estrita na primeira checagem, simulando "cache desatualizado".
        result = scraper.scrape_profile(
            "perfil_fallback",
            window_days=0,
            fetch_fn=fetch_fn_network_error,
            throttle_fn=lambda: None,
            db_path=db_path,
        )

        assert result is not None
        assert result["profile"]["username"] == "perfil_fallback"
        assert result["profile"]["followers_count"] == 300
    finally:
        os.unlink(db_path)


def test_scrape_profile_raises_scraper_unavailable_error_when_fetch_fails_and_no_cache():
    db_path = make_temp_db()
    try:
        def fetch_fn_network_error(username, cookies):
            raise ConnectionError("instagram bloqueou a coleta")

        try:
            scraper.scrape_profile(
                "perfil_sem_cache_nenhum",
                window_days=90,
                fetch_fn=fetch_fn_network_error,
                throttle_fn=lambda: None,
                db_path=db_path,
            )
            assert False, "esperava ScraperUnavailableError"
        except scraper.ScraperUnavailableError:
            pass
    finally:
        os.unlink(db_path)


def test_instaloader_fetch_fn_maps_profile_and_posts_without_network(monkeypatch):
    class FakePost:
        def __init__(self, mediaid, shortcode, caption, likes, comments):
            self.mediaid = mediaid
            self.shortcode = shortcode
            self.caption = caption
            self.likes = likes
            self.comments = comments

    class FakeProfile:
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            return iter([FakePost(1, "abc", "legenda", 10, 2)])

    class FakeContext:
        pass

    class FakeInstaloader:
        def __init__(self):
            self.context = FakeContext()
            self.loaded_session = None

        def load_session_from_file(self, username, filename):
            self.loaded_session = (username, filename)

    monkeypatch.setattr(scraper.instaloader, "Instaloader", FakeInstaloader)
    monkeypatch.setattr(
        scraper.instaloader.Profile,
        "from_username",
        staticmethod(lambda context, username: FakeProfile()),
    )

    result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    assert result["bio"] == "bio fake"
    assert result["followers_count"] == 1234
    assert result["posts"][0]["post_id"] == "1"
    assert result["posts"][0]["likes_count"] == 10
    assert result["posts"][0]["comments_count"] == 2
