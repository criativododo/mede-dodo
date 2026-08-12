import itertools
import random
import time

import instaloader

from src import database

MAX_POSTS_PER_FETCH = 12


class ScraperUnavailableError(Exception):
    """Erro quando a coleta real falha e não há nenhum cache disponível como fallback."""


def throttle(min_seconds=2, max_seconds=5, sleep_fn=time.sleep, random_fn=random.uniform):
    delay = random_fn(min_seconds, max_seconds)
    sleep_fn(delay)
    return delay


def instaloader_fetch_fn(username, cookies=None):
    # cookies, se fornecido, é o caminho de um arquivo de sessão local salvo
    # previamente via Instaloader.save_session_to_file (login manual único, fora
    # deste código) — evita reautenticar a cada coleta.
    loader = instaloader.Instaloader()
    if cookies:
        loader.load_session_from_file(username, filename=cookies)

    profile = instaloader.Profile.from_username(loader.context, username)

    posts = []
    # get_posts() pagina via rede a cada bloco; limitamos a MAX_POSTS_PER_FETCH
    # para não gerar chamadas extras além do necessário para a janela de análise.
    for post in itertools.islice(profile.get_posts(), MAX_POSTS_PER_FETCH):
        posts.append(
            {
                "post_id": str(post.mediaid),
                "raw": {"shortcode": post.shortcode, "caption": post.caption},
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
