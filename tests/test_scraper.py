import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import instaloader

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


class FakeOwner:
    def __init__(self, username):
        self.username = username


class FakeAnswer:
    def __init__(self, owner_username):
        self.owner = FakeOwner(owner_username)


class FakeComment:
    def __init__(self, owner_username, text, answers=None):
        self.owner = FakeOwner(owner_username)
        self.text = text
        self.answers = answers or []


class FakePost:
    def __init__(
        self, mediaid, shortcode, caption, likes, comments_count, date_utc,
        comments=None, comments_error=None,
    ):
        self.mediaid = mediaid
        self.shortcode = shortcode
        self.caption = caption
        self.likes = likes
        self.comments = comments_count
        self.date_utc = date_utc
        self._comments = comments or []
        self._comments_error = comments_error

    def get_comments(self):
        def _generator():
            for comment in self._comments:
                yield comment
            if self._comments_error:
                raise self._comments_error

        return _generator()


class FakeContext:
    pass


class FakeInstaloader:
    def __init__(self):
        self.context = FakeContext()
        self.loaded_session = None

    def load_session_from_file(self, username, filename=None):
        self.loaded_session = (username, filename)


def _patch_fake_profile(monkeypatch, fake_profile):
    monkeypatch.setattr(scraper.instaloader, "Instaloader", FakeInstaloader)
    monkeypatch.setattr(
        scraper.instaloader.Profile,
        "from_username",
        staticmethod(lambda context, username: fake_profile),
    )


def test_instaloader_fetch_fn_maps_profile_and_posts_without_network(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)
            return iter([FakePost(1, "abc", "legenda", 10, 2, recent)])

    _patch_fake_profile(monkeypatch, FakeProfile())

    result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    assert result["bio"] == "bio fake"
    assert result["followers_count"] == 1234
    assert result["posts"][0]["post_id"] == "1"
    assert result["posts"][0]["likes_count"] == 10
    assert result["posts"][0]["comments_count"] == 2


def test_instaloader_fetch_fn_extracts_real_comments_with_username_and_text(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)
            comments = [FakeComment("ana_silva92", "Quanto custa?")]
            return iter([FakePost(1, "abc", "legenda", 10, 1, recent, comments=comments)])

    _patch_fake_profile(monkeypatch, FakeProfile())

    result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    real_comments = result["posts"][0]["raw"]["comments"]
    assert real_comments == [{"username": "ana_silva92", "texto": "Quanto custa?", "respondido": False}]


def test_instaloader_fetch_fn_marks_respondido_true_when_creator_replies(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)
            comments = [
                FakeComment("ana_silva92", "Quanto custa?", answers=[FakeAnswer("perfil_fake")]),
                FakeComment("joao99", "Lindo", answers=[FakeAnswer("outra_pessoa")]),
            ]
            return iter([FakePost(1, "abc", "legenda", 10, 2, recent, comments=comments)])

    _patch_fake_profile(monkeypatch, FakeProfile())

    result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    real_comments = result["posts"][0]["raw"]["comments"]
    assert real_comments[0]["respondido"] is True
    assert real_comments[1]["respondido"] is False


def test_instaloader_fetch_fn_excludes_posts_older_than_max_window_days(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=5)
            old = datetime.now(timezone.utc) - timedelta(days=scraper.MAX_WINDOW_DAYS + 10)
            return iter(
                [
                    FakePost(1, "recente", "legenda recente", 10, 0, recent),
                    FakePost(2, "antigo", "legenda antiga", 10, 0, old),
                ]
            )

    _patch_fake_profile(monkeypatch, FakeProfile())

    result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    post_ids = [p["post_id"] for p in result["posts"]]
    assert post_ids == ["1"]


def test_instaloader_fetch_fn_stops_at_safety_cap_of_posts(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)

            def _generate():
                for i in range(scraper.MAX_POSTS_SAFETY_CAP + 20):
                    yield FakePost(i, f"sc{i}", "legenda", 1, 0, recent)

            return _generate()

    _patch_fake_profile(monkeypatch, FakeProfile())

    result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    assert len(result["posts"]) == scraper.MAX_POSTS_SAFETY_CAP


def make_session_dir(tmp_path, *usernames):
    session_dir = tmp_path / "instaloader"
    session_dir.mkdir()
    for username in usernames:
        (session_dir / f"session-{username}").write_bytes(b"cookie-jar-fake")
    return str(session_dir)


def test_detect_available_session_username_finds_file_without_loading(tmp_path, monkeypatch):
    session_dir = make_session_dir(tmp_path, "criativododo")
    monkeypatch.setattr(scraper, "SESSION_DIR", session_dir)

    assert scraper.detect_available_session_username() == "criativododo"


def test_detect_available_session_username_returns_none_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(scraper, "SESSION_DIR", str(tmp_path / "nao_existe"))

    assert scraper.detect_available_session_username() is None


def test_load_any_available_session_loads_first_matching_session_file(tmp_path, monkeypatch):
    session_dir = make_session_dir(tmp_path, "criativododo")
    monkeypatch.setattr(scraper, "SESSION_DIR", session_dir)
    loader = FakeInstaloader()

    loaded_username = scraper.load_any_available_session(loader)

    assert loaded_username == "criativododo"
    assert loader.loaded_session == ("criativododo", os.path.join(session_dir, "session-criativododo"))


def test_load_any_available_session_returns_none_when_no_session_files(tmp_path, monkeypatch):
    session_dir = str(tmp_path / "instaloader_vazio")
    os.makedirs(session_dir)
    monkeypatch.setattr(scraper, "SESSION_DIR", session_dir)
    loader = FakeInstaloader()

    loaded_username = scraper.load_any_available_session(loader)

    assert loaded_username is None
    assert loader.loaded_session is None


def test_load_any_available_session_skips_unreadable_file_and_tries_next(tmp_path, monkeypatch):
    session_dir = make_session_dir(tmp_path, "conta_corrompida", "criativododo")
    monkeypatch.setattr(scraper, "SESSION_DIR", session_dir)

    class FlakyInstaloader(FakeInstaloader):
        def load_session_from_file(self, username, filename=None):
            if username == "conta_corrompida":
                raise instaloader.exceptions.LoginException("sessão corrompida")
            super().load_session_from_file(username, filename)

    loader = FlakyInstaloader()

    loaded_username = scraper.load_any_available_session(loader)

    assert loaded_username == "criativododo"


def test_instaloader_fetch_fn_auto_loads_available_session_when_no_cookies_given(tmp_path, monkeypatch):
    session_dir = make_session_dir(tmp_path, "criativododo")
    monkeypatch.setattr(scraper, "SESSION_DIR", session_dir)

    created_loaders = []

    class TrackedFakeInstaloader(FakeInstaloader):
        def __init__(self):
            super().__init__()
            created_loaders.append(self)

    class FakeProfile:
        username = "silviabraz"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            return iter([])

    monkeypatch.setattr(scraper.instaloader, "Instaloader", TrackedFakeInstaloader)
    monkeypatch.setattr(
        scraper.instaloader.Profile,
        "from_username",
        staticmethod(lambda context, username: FakeProfile()),
    )

    scraper.instaloader_fetch_fn("silviabraz", cookies=None)

    assert len(created_loaders) == 1
    assert created_loaders[0].loaded_session == (
        "criativododo",
        os.path.join(session_dir, "session-criativododo"),
    )


def test_instaloader_fetch_fn_uses_session_owner_username_from_cookies_path_not_target_profile(monkeypatch):
    # Regressão: `cookies` aponta para o arquivo de sessão da CONTA LOGADA
    # (ex.: "criativododo"), que quase nunca é o mesmo perfil sendo analisado
    # (ex.: "silviabraz"). Antes, o código chamava
    # load_session_from_file(username=<perfil analisado>, ...), misturando a
    # identidade da sessão com a do alvo da raspagem.
    created_loaders = []

    class TrackedFakeInstaloader(FakeInstaloader):
        def __init__(self):
            super().__init__()
            created_loaders.append(self)

    class FakeProfile:
        username = "silviabraz"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            return iter([])

    monkeypatch.setattr(scraper.instaloader, "Instaloader", TrackedFakeInstaloader)
    monkeypatch.setattr(
        scraper.instaloader.Profile,
        "from_username",
        staticmethod(lambda context, username: FakeProfile()),
    )

    cookies_path = "/home/user/.config/instaloader/session-criativododo"
    result = scraper.instaloader_fetch_fn("silviabraz", cookies=cookies_path)

    assert result["bio"] == "bio fake"
    assert created_loaders[0].loaded_session == ("criativododo", cookies_path)


DELETED_SCHEMA_400_MSG = (
    'JSON Query to api/v1/users/web_profile_info/?username=silviabraz: '
    '400 Bad Request - "fail" status, message "Asset '
    'asset://laser.provider/ig_business_category_subvertical has been deleted. '
    'You cannot use this schema" when accessing '
    'https://www.instagram.com/api/v1/users/web_profile_info/?username=silviabraz'
)


def test_fetch_real_comments_returns_partial_data_when_comment_fetch_fails_partway(caplog):
    # Regressão: um bug real do Instagram apareceu ao vivo em @caroline_tanaka —
    # a busca de comentários de UM post falhou no meio da paginação
    # (ConnectionException do Instaloader) e derrubava a coleta inteira do perfil.
    post = FakePost(
        1, "abc", "legenda", 10, 2, datetime.now(timezone.utc),
        comments=[FakeComment("ana_silva92", "Quanto custa?")],
        comments_error=instaloader.exceptions.ConnectionException("something went wrong"),
    )

    with caplog.at_level("WARNING"):
        comments = scraper._fetch_real_comments(post, "perfil_fake")

    assert comments == [{"username": "ana_silva92", "texto": "Quanto custa?", "respondido": False}]
    assert "abc" in caplog.text or "perfil_fake" in caplog.text


def test_instaloader_fetch_fn_continues_to_next_post_when_one_posts_comments_fail(monkeypatch, caplog):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)
            return iter(
                [
                    FakePost(
                        1, "post_com_falha", "legenda 1", 10, 0, recent,
                        comments_error=instaloader.exceptions.ConnectionException("something went wrong"),
                    ),
                    FakePost(
                        2, "post_ok", "legenda 2", 5, 1, recent,
                        comments=[FakeComment("joao99", "Lindo")],
                    ),
                ]
            )

    _patch_fake_profile(monkeypatch, FakeProfile())

    with caplog.at_level("WARNING"):
        result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    # A coleta não é interrompida: os dois posts aparecem no resultado.
    assert [p["post_id"] for p in result["posts"]] == ["1", "2"]
    assert result["posts"][0]["raw"]["comments"] == []
    assert result["posts"][1]["raw"]["comments"] == [
        {"username": "joao99", "texto": "Lindo", "respondido": False}
    ]


def test_instaloader_fetch_fn_raises_clear_error_on_deleted_schema_400(monkeypatch, caplog):
    # Regressão: reproduz ao vivo em @silviabraz — Profile.from_username() levanta
    # ConnectionException com o Erro HTTP 400 de schema removido no backend do
    # Instagram (endpoint web_profile_info), mesmo com sessão autenticada.
    def _raise_deleted_schema(context, username):
        raise instaloader.exceptions.ConnectionException(DELETED_SCHEMA_400_MSG)

    monkeypatch.setattr(scraper.instaloader, "Instaloader", FakeInstaloader)
    monkeypatch.setattr(scraper.instaloader.Profile, "from_username", staticmethod(_raise_deleted_schema))

    with caplog.at_level("ERROR"):
        try:
            scraper.instaloader_fetch_fn("silviabraz", cookies=None)
            assert False, "esperava ScraperUnavailableError"
        except scraper.ScraperUnavailableError as exc:
            message = str(exc).lower()
            assert "schema" in message or "web_profile_info" in message
            assert "instagram" in message

    assert "silviabraz" in caplog.text


def test_instaloader_fetch_fn_reraises_other_connection_errors_for_profile_resolution(monkeypatch):
    # Erros de conexão que NÃO são o bug de schema conhecido continuam propagando
    # sem reclassificação — scrape_profile() já sabe convertê-los em
    # ScraperUnavailableError (com fallback de cache) no nível acima.
    def _raise_generic_connection_error(context, username):
        raise instaloader.exceptions.ConnectionException("Instagram bloqueou temporariamente")

    monkeypatch.setattr(scraper.instaloader, "Instaloader", FakeInstaloader)
    monkeypatch.setattr(
        scraper.instaloader.Profile, "from_username", staticmethod(_raise_generic_connection_error)
    )

    try:
        scraper.instaloader_fetch_fn("perfil_qualquer", cookies=None)
        assert False, "esperava ConnectionException"
    except instaloader.exceptions.ConnectionException as exc:
        assert "bloqueou" in str(exc)
