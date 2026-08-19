"""Testes unitários da ISSUE-002: cache SQLite, helper de segredos e scraper mockado."""

import sqlite3
from datetime import datetime, timedelta, timezone

import instaloader
import pytest

from src.features.coleta import auth, database, scraper


# --- database.py -----------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "cache_test.db"


def test_save_and_get_cached_profile_valid(db_path):
    database.save_profile_cache(
        "@exemplo",
        {"bio": "oi", "followers_count": 100},
        [{"post_id": "1"}],
        [{"texto": "bom"}],
        db_path=db_path,
    )
    cached = database.get_cached_profile("@exemplo", db_path=db_path)

    assert cached is not None
    assert cached["profile_data"]["followers_count"] == 100
    assert cached["posts_data"] == [{"post_id": "1"}]
    assert cached["comments_data"] == [{"texto": "bom"}]
    assert cached["age_seconds"] < 60


def test_get_cached_profile_missing_returns_none(db_path):
    assert database.get_cached_profile("@inexistente", db_path=db_path) is None


def test_username_normalization_ignores_leading_at(db_path):
    database.save_profile_cache("exemplo", {"bio": ""}, [], [], db_path=db_path)
    assert database.get_cached_profile("@exemplo", db_path=db_path) is not None


def test_ttl_expiration(db_path):
    database.save_profile_cache("expira", {"bio": ""}, [], [], ttl_seconds=86400, db_path=db_path)

    conn = sqlite3.connect(db_path)
    expired_created_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    conn.execute(
        "UPDATE profile_cache SET created_at_utc = ? WHERE username = ?",
        (expired_created_at, "expira"),
    )
    conn.commit()
    conn.close()

    assert database.get_cached_profile("expira", db_path=db_path) is None


def test_ttl_not_yet_expired(db_path):
    database.save_profile_cache("fresco", {"bio": ""}, [], [], ttl_seconds=86400, db_path=db_path)
    cached = database.get_cached_profile("fresco", db_path=db_path)

    assert cached is not None
    assert cached["age_seconds"] < 86400


# --- auth.py -----------------------------------------------------------


def test_get_secret_reads_from_environ(monkeypatch):
    monkeypatch.setenv("MEDE_DODO_TEST_KEY", "valor-teste")
    assert auth.get_secret("MEDE_DODO_TEST_KEY") == "valor-teste"


def test_get_secret_returns_default_when_missing(monkeypatch):
    monkeypatch.delenv("MEDE_DODO_TEST_KEY_INEXISTENTE", raising=False)
    assert auth.get_secret("MEDE_DODO_TEST_KEY_INEXISTENTE", default="padrao") == "padrao"


# --- scraper.py (mockado) -----------------------------------------------------------


class _FakeOwner:
    def __init__(self, username):
        self.username = username


class _FakeComment:
    def __init__(self, username, text):
        self.owner = _FakeOwner(username)
        self.text = text


class _FakePost:
    def __init__(self, mediaid, typename, date_utc, likes, comments_count, caption, comments):
        self.mediaid = mediaid
        self.typename = typename
        self.date_utc = date_utc
        self.likes = likes
        self.comments = comments_count
        self.caption = caption
        self.shortcode = f"sc{mediaid}"
        self._comments = comments

    def get_comments(self):
        return iter(self._comments)


class _FakeProfile:
    def __init__(self, posts, biography="bio de teste", followers=1000):
        self._posts = posts
        self.biography = biography
        self.followers = followers

    def get_posts(self):
        return iter(self._posts)


def test_collect_profile_success(monkeypatch, db_path):
    now = datetime.now(timezone.utc)
    fake_post = _FakePost(
        mediaid=111,
        typename="GraphVideo",
        date_utc=now - timedelta(days=1),
        likes=50,
        comments_count=2,
        caption="Adorei essa parceria #publi",
        comments=[_FakeComment("fan1", "lindo"), _FakeComment("fan2", "quero")],
    )
    fake_profile = _FakeProfile([fake_post])

    monkeypatch.setattr(scraper.instaloader.Profile, "from_username", lambda ctx, u: fake_profile)
    monkeypatch.setattr(scraper, "_load_persisted_session", lambda loader: None)

    result = scraper.collect_profile("exemplo", db_path=db_path, sleep_fn=lambda s: None)

    assert result["status"] == "ok"
    assert result["source"] == "real"
    assert len(result["posts_data"]) == 1
    assert result["posts_data"][0]["format"] == "Reel"
    assert result["posts_data"][0]["is_sponsored"] is True
    assert len(result["comments_data"]) == 2

    cached = database.get_cached_profile("exemplo", db_path=db_path)
    assert cached is not None
    assert cached["profile_data"]["followers_count"] == 1000


def test_collect_profile_skips_posts_outside_window(monkeypatch, db_path):
    """Com >= MIN_POSTS_IN_WINDOW posts dentro da janela, o post antigo (fora
    da janela) é excluído normalmente — sem acionar o fallback de janela
    estendida."""
    now = datetime.now(timezone.utc)
    posts = [
        _FakePost(1, "GraphImage", now - timedelta(days=200), 10, 0, "antigo", []),
        _FakePost(2, "GraphImage", now - timedelta(days=5), 20, 0, "recente1", []),
        _FakePost(3, "GraphImage", now - timedelta(days=6), 20, 0, "recente2", []),
        _FakePost(4, "GraphImage", now - timedelta(days=7), 20, 0, "recente3", []),
    ]
    fake_profile = _FakeProfile(posts)

    monkeypatch.setattr(scraper.instaloader.Profile, "from_username", lambda ctx, u: fake_profile)
    monkeypatch.setattr(scraper, "_load_persisted_session", lambda loader: None)

    result = scraper.collect_profile("exemplo", db_path=db_path, sleep_fn=lambda s: None)

    assert len(result["posts_data"]) == 3
    assert [p["post_id"] for p in result["posts_data"]] == ["2", "3", "4"]
    assert result["warnings"] == []


def test_collect_profile_extends_window_when_too_few_recent_posts(monkeypatch, db_path):
    """Perfil com menos de MIN_POSTS_IN_WINDOW posts nos últimos 90 dias cai
    para os últimos posts mais recentes disponíveis, com warning explícito —
    em vez de uma auditoria vazia."""
    now = datetime.now(timezone.utc)
    posts = [
        _FakePost(1, "GraphImage", now - timedelta(days=5), 10, 0, "recente", []),
        _FakePost(2, "GraphImage", now - timedelta(days=150), 20, 0, "antigo1", []),
        _FakePost(3, "GraphImage", now - timedelta(days=200), 20, 0, "antigo2", []),
    ]
    fake_profile = _FakeProfile(posts)

    monkeypatch.setattr(scraper.instaloader.Profile, "from_username", lambda ctx, u: fake_profile)
    monkeypatch.setattr(scraper, "_load_persisted_session", lambda loader: None)

    result = scraper.collect_profile("exemplo", db_path=db_path, sleep_fn=lambda s: None)

    assert [p["post_id"] for p in result["posts_data"]] == ["1", "2", "3"]
    assert len(result["warnings"]) == 1
    assert "Janela estendida" in result["warnings"][0]


def test_collect_profile_falls_back_to_cache_on_rate_limit(monkeypatch, db_path):
    database.save_profile_cache("exemplo", {"bio": "old"}, [{"post_id": "1"}], [], db_path=db_path)

    def _raise(ctx, username):
        raise instaloader.exceptions.TooManyRequestsException("429 please slow down")

    monkeypatch.setattr(scraper.instaloader.Profile, "from_username", _raise)
    monkeypatch.setattr(scraper, "_load_persisted_session", lambda loader: None)

    result = scraper.collect_profile("exemplo", db_path=db_path)

    assert result["status"] == "cache_fallback"
    assert result["source"] == "cache"
    assert result["error_reason"] == "rate_limit"


def test_collect_profile_raises_when_no_cache_available(monkeypatch, db_path):
    def _raise(ctx, username):
        raise instaloader.exceptions.TooManyRequestsException("429")

    monkeypatch.setattr(scraper.instaloader.Profile, "from_username", _raise)
    monkeypatch.setattr(scraper, "_load_persisted_session", lambda loader: None)

    with pytest.raises(scraper.ScraperError) as exc_info:
        scraper.collect_profile("sem-cache", db_path=db_path)

    assert exc_info.value.status_code == 429
    assert exc_info.value.reason == "rate_limit"


# --- fallback GraphQL de comentários (PROGRESS.md §3 — bug do endpoint nativo) ----------------------------


class _FakeGraphQLContext:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def graphql_query(self, query_hash, variables):
        self.calls.append((query_hash, variables))
        return self._response


class _FakePostBrokenComments:
    """Post cujo `get_comments()` nativo falha sem coletar nada — só o
    fallback via GraphQL direto devolve comentários."""

    def __init__(self, mediaid, date_utc, graphql_response):
        self.mediaid = mediaid
        self.typename = "GraphImage"
        self.date_utc = date_utc
        self.likes = 5
        self.comments = 1
        self.caption = "post normal"
        self.shortcode = f"sc{mediaid}"
        self._context = _FakeGraphQLContext(graphql_response)

    def get_comments(self):
        raise instaloader.exceptions.ConnectionException("something went wrong")


def test_fetch_post_comments_falls_back_to_graphql_when_native_endpoint_fails():
    graphql_response = {
        "data": {
            "shortcode_media": {
                "edge_media_to_parent_comment": {
                    "edges": [
                        {"node": {"text": "lindo demais", "owner": {"username": "fan_graphql"}}},
                    ]
                }
            }
        }
    }
    post = _FakePostBrokenComments(999, datetime.now(timezone.utc), graphql_response)

    comments = scraper._fetch_post_comments(post, sleep_fn=lambda s: None)

    assert comments == [
        {"post_id": "999", "username": "fan_graphql", "display_name": None, "texto": "lindo demais"}
    ]
    assert post._context.calls[0][1]["shortcode"] == "sc999"


def test_collect_profile_recovers_comments_via_graphql_fallback(monkeypatch, db_path):
    graphql_response = {
        "data": {
            "shortcode_media": {
                "edge_media_to_parent_comment": {
                    "edges": [{"node": {"text": "quero comprar", "owner": {"username": "fan2"}}}]
                }
            }
        }
    }
    now = datetime.now(timezone.utc)
    posts = [
        _FakePostBrokenComments(1, now - timedelta(days=1), graphql_response),
        _FakePostBrokenComments(2, now - timedelta(days=2), graphql_response),
        _FakePostBrokenComments(3, now - timedelta(days=3), graphql_response),
    ]
    fake_profile = _FakeProfile(posts)

    monkeypatch.setattr(scraper.instaloader.Profile, "from_username", lambda ctx, u: fake_profile)
    monkeypatch.setattr(scraper, "_load_persisted_session", lambda loader: None)

    result = scraper.collect_profile("exemplo", db_path=db_path, sleep_fn=lambda s: None)

    assert len(result["posts_data"]) == 3
    assert len(result["comments_data"]) == 3
    assert all(c["texto"] == "quero comprar" for c in result["comments_data"])


# --- nome de exibição real do comentarista (demografia IBGE) -----------------------------------------------


class _FakeOwnerNode:
    """Simula `PostComment` com um comentário vindo do endpoint iPhone
    (`iphone_struct` já presente localmente) — extrair o nome de exibição
    aqui nunca deve disparar rede."""

    def __init__(self, username, text, full_name=None):
        self.text = text
        self.owner = _FakeOwner(username)
        self._node = {"iphone_struct": {"user": {"full_name": full_name}}} if full_name else {}

    def get_comments(self):
        return iter([])


def test_extract_comment_owner_display_name_reads_local_iphone_struct():
    comment = _FakeOwnerNode("ana.paula123", "amei", full_name="Ana Paula")
    assert scraper._extract_comment_owner_display_name(comment) == "Ana Paula"


def test_extract_comment_owner_display_name_returns_none_without_iphone_struct():
    comment = _FakeComment("ana.paula123", "amei")
    assert scraper._extract_comment_owner_display_name(comment) is None
