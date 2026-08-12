import random
import time

from src import database


def throttle(min_seconds=2, max_seconds=5, sleep_fn=time.sleep, random_fn=random.uniform):
    delay = random_fn(min_seconds, max_seconds)
    sleep_fn(delay)
    return delay


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
    raw = fetch_fn(username, cookies)
    database.save_profile_data(
        username,
        raw.get("posts", []),
        bio=raw.get("bio"),
        followers_count=raw.get("followers_count"),
        db_path=db_path,
    )
    return database.get_cached_data(username, window_days, db_path=db_path)
