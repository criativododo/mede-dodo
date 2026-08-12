import random
import time
from datetime import datetime, timedelta, timezone

import instaloader

from src import database

# Maior janela selecionável em app.py (WINDOW_OPTIONS = [30, 60, 90]) — a coleta real
# nunca busca posts mais antigos que isso, senão a "janela de análise" da UI não
# corresponderia aos posts realmente varridos.
MAX_WINDOW_DAYS = 90
# Teto de segurança contra paginação sem fim em perfis muito ativos — protege throttling
# e cota de requisições mesmo que MAX_WINDOW_DAYS não seja atingido (DUMMY.md regra 3).
MAX_POSTS_SAFETY_CAP = 60


class ScraperUnavailableError(Exception):
    """Erro quando a coleta real falha e não há nenhum cache disponível como fallback."""


def throttle(min_seconds=2, max_seconds=5, sleep_fn=time.sleep, random_fn=random.uniform):
    delay = random_fn(min_seconds, max_seconds)
    sleep_fn(delay)
    return delay


def _post_date_utc(post):
    post_date = post.date_utc
    if post_date.tzinfo is None:
        post_date = post_date.replace(tzinfo=timezone.utc)
    return post_date


def _fetch_real_comments(post, profile_username):
    # RF-06/RF-08 dependem de comentário real (autor + texto), não só da contagem
    # agregada de post.comments (int) — sem isso, demografia/pods/resposta da
    # criadora não têm nenhum dado para trabalhar em perfis reais.
    comments = []
    for comment in post.get_comments():
        owner_username = getattr(comment.owner, "username", None)
        respondido = any(
            getattr(getattr(answer, "owner", None), "username", None) == profile_username
            for answer in (comment.answers or [])
        )
        comments.append({"username": owner_username, "texto": comment.text, "respondido": respondido})
    return comments


def instaloader_fetch_fn(username, cookies=None):
    # cookies, se fornecido, é o caminho de um arquivo de sessão local salvo
    # previamente via Instaloader.save_session_to_file (login manual único, fora
    # deste código) — evita reautenticar a cada coleta.
    loader = instaloader.Instaloader()
    if cookies:
        loader.load_session_from_file(username, filename=cookies)

    profile = instaloader.Profile.from_username(loader.context, username)
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_WINDOW_DAYS)

    posts = []
    # get_posts() retorna do mais recente para o mais antigo — para assim que um post
    # sair da maior janela selecionável (MAX_WINDOW_DAYS) ou ao atingir o teto de
    # segurança, o que vier primeiro.
    for post in profile.get_posts():
        if len(posts) >= MAX_POSTS_SAFETY_CAP:
            break

        post_date = _post_date_utc(post)
        if post_date < cutoff:
            break

        posts.append(
            {
                "post_id": str(post.mediaid),
                "raw": {
                    "shortcode": post.shortcode,
                    "caption": post.caption,
                    "published_at": post_date.isoformat(),
                    "comments": _fetch_real_comments(post, profile.username),
                },
                "likes_count": post.likes,
                "comments_count": post.comments,
            }
        )

    return {
        "bio": profile.biography,
        "followers_count": profile.followers,
        "posts": posts,
    }


def scrape_profile(
    username,
    window_days=90,
    cookies=None,
    fetch_fn=None,
    throttle_fn=throttle,
    db_path=database.DB_PATH,
):
    cached = database.get_cached_data(username, window_days, db_path=db_path)
    if cached is not None:
        return cached

    if fetch_fn is None:
        raise NotImplementedError(
            "fetch_fn não fornecido: a estratégia real de raspagem do Instagram "
            "(sessão/cookies) ainda depende de uma issue de integração futura."
        )

    throttle_fn()
    try:
        raw = fetch_fn(username, cookies)
    except Exception as exc:
        fallback = database.get_cached_data(username, window_days=None, db_path=db_path)
        if fallback is not None:
            return fallback
        raise ScraperUnavailableError(
            f"Falha ao coletar dados de '{username}' e nenhum cache disponível: {exc}"
        ) from exc

    database.save_profile_data(
        username,
        raw.get("posts", []),
        bio=raw.get("bio"),
        followers_count=raw.get("followers_count"),
        db_path=db_path,
    )
    return database.get_cached_data(username, window_days, db_path=db_path)
