import glob
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone

import instaloader

from src import database
from src import rate_controller as rate_controller_module

_logger = logging.getLogger(__name__)

# Assinatura textual do bug atual no backend do próprio Instagram no endpoint
# web_profile_info (reproduzido ao vivo em 2026-08-12 contra @silviabraz, mesmo
# com sessão autenticada): um campo de schema interno foi removido do lado deles.
# Não é falha de sessão/autenticação local — não há contorno no lado do cliente
# na API pública do Instaloader (Profile.from_username não oferece endpoint
# alternativo nesta versão).
_DELETED_SCHEMA_SIGNATURE = "has been deleted. you cannot use this schema"

# Sinais textuais de checkpoint/challenge do Instagram (Instaloader não expõe
# uma exceção dedicada para isso — surge como ConnectionException com uma
# dessas strings na mensagem, conforme troubleshooting.html da lib, ref. [1]
# no FINDER-003). Pausa e pede ação humana — nunca contorna (FINDER-003 §4.4).
_CHECKPOINT_SIGNATURES = ("checkpoint_required", "challenge_required")


def _is_checkpoint_signal(exc_text):
    lowered = exc_text.lower()
    return any(signature in lowered for signature in _CHECKPOINT_SIGNATURES)

# Maior janela selecionável em app.py (WINDOW_OPTIONS = [30, 60, 90]) — a coleta real
# nunca busca posts mais antigos que isso, senão a "janela de análise" da UI não
# corresponderia aos posts realmente varridos.
MAX_WINDOW_DAYS = 90
# Teto de segurança contra paginação sem fim em perfis muito ativos — protege throttling
# e cota de requisições mesmo que MAX_WINDOW_DAYS não seja atingido (DUMMY.md regra 3).
MAX_POSTS_SAFETY_CAP = 60

# Local padrão onde `instaloader -l <usuario>` (login manual, fora deste código) salva
# arquivos de sessão: um por conta, nomeado "session-<usuario>".
SESSION_DIR = os.path.join(os.path.expanduser("~"), ".config", "instaloader")
SESSION_FILE_PREFIX = "session-"


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


# query_hash da consulta GraphQL legada de comentários de post — a mesma que
# Post.get_comments() já usa nativamente para posts com poucos comentários
# (<= instaloader.NodeIterator.page_length()). Usamos aqui como fallback também
# para posts com MUITOS comentários, cujo get_comments() sempre roteia para o
# endpoint do app iPhone (_get_comments_via_iphone_endpoint, fallback da própria
# lib para a issue #2125 dela) — endpoint que está falhando de forma sistemática
# no backend do Instagram (reproduzido ao vivo contra vários posts de
# @silviabraz em 2026-08-12, sempre com o mesmo erro genérico "something went
# wrong", nunca um sucesso pontual).
_COMMENTS_GRAPHQL_QUERY_HASH = "97b41c52301f77ce508f55e66d17620e"
_COMMENTS_GRAPHQL_FIRST_PAGE_SIZE = 50


def _fetch_comments_first_page_via_graphql(post, profile_username):
    """Busca só a 1ª página de comentários reais via GraphQL direto, como último
    recurso quando post.get_comments() falha sem coletar nada. Paginação além da
    1ª página não é confiável nesse endpoint legado (mesma issue #2125 acima),
    então não tentamos ir além — uma amostra real de comentários é preferível a
    zero para demografia/antifraude. Retorna lista vazia se esta tentativa
    também falhar (mantém o comportamento resiliente já existente)."""
    try:
        data = post._context.graphql_query(
            _COMMENTS_GRAPHQL_QUERY_HASH,
            {"shortcode": post.shortcode, "first": _COMMENTS_GRAPHQL_FIRST_PAGE_SIZE},
        )
        edges = data["data"]["shortcode_media"]["edge_media_to_parent_comment"]["edges"]
    except Exception as exc:
        _logger.warning(
            "Fallback via GraphQL direto para comentários do post %s de '%s' "
            "também falhou: %s", getattr(post, "shortcode", "?"), profile_username, exc,
        )
        return []

    comments = []
    for edge in edges:
        node = edge.get("node") or {}
        owner_username = (node.get("owner") or {}).get("username")
        threaded_edges = ((node.get("edge_threaded_comments") or {}).get("edges")) or []
        respondido = any(
            ((answer.get("node") or {}).get("owner") or {}).get("username") == profile_username
            for answer in threaded_edges
        )
        comments.append({"username": owner_username, "texto": node.get("text"), "respondido": respondido})
    return comments


def _fetch_real_comments(post, profile_username):
    # RF-06/RF-08 dependem de comentário real (autor + texto), não só da contagem
    # agregada de post.comments (int) — sem isso, demografia/pods/resposta da
    # criadora não têm nenhum dado para trabalhar em perfis reais.
    comments = []
    try:
        for comment in post.get_comments():
            owner_username = getattr(comment.owner, "username", None)
            respondido = any(
                getattr(getattr(answer, "owner", None), "username", None) == profile_username
                for answer in (comment.answers or [])
            )
            comments.append({"username": owner_username, "texto": comment.text, "respondido": respondido})
    except instaloader.exceptions.ConnectionException as exc:
        # Bug real observado ao vivo em @caroline_tanaka: a busca de comentários de
        # UM post pode falhar no meio da paginação (rate limit/instabilidade do
        # endpoint de comentários do app iPhone). Mantém os comentários já obtidos
        # (dados parciais) e segue em frente — não deve derrubar a coleta do post
        # nem dos demais posts/perfis do pipeline.
        _logger.warning(
            "Falha de conexão ao buscar comentários do post %s de '%s' — mantendo %d "
            "comentário(s) já coletado(s) e seguindo em frente: %s",
            getattr(post, "shortcode", "?"), profile_username, len(comments), exc,
        )
        if not comments:
            comments = _fetch_comments_first_page_via_graphql(post, profile_username)
    except Exception as exc:
        # Qualquer outra falha inesperada na busca de comentários também não deve
        # derrubar a coleta do perfil — só o post afetado fica com dados parciais.
        _logger.warning(
            "Falha inesperada ao buscar comentários do post %s de '%s' — mantendo %d "
            "comentário(s) já coletado(s) e seguindo em frente: %s",
            getattr(post, "shortcode", "?"), profile_username, len(comments), exc,
        )
        if not comments:
            comments = _fetch_comments_first_page_via_graphql(post, profile_username)
    return comments


def _session_username_from_path(path):
    """Deriva o dono da sessão (ex.: "criativododo") a partir do nome de arquivo
    "session-<usuario>" — NÃO é o perfil sendo analisado. Sem isso,
    load_session_from_file() era chamado com o username do perfil-alvo (ex.:
    "silviabraz"), uma identidade que não bate com os cookies carregados."""
    basename = os.path.basename(path)
    if basename.startswith(SESSION_FILE_PREFIX):
        return basename[len(SESSION_FILE_PREFIX):]
    return None


def load_any_available_session(L):
    """Detecta arquivos de sessão salvos em SESSION_DIR (session-<usuario>) e
    carrega o primeiro que funcionar no Instaloader `L`, autenticando o
    contexto sem exigir INSTAGRAM_SESSION_FILE explícito. Necessário porque
    perfis business/creator devolvem Erro HTTP 400 (endpoint web_profile_info
    anônimo) quando a coleta roda sem sessão autenticada.

    Retorna o username da sessão carregada, ou None se nenhum arquivo de
    sessão foi encontrado ou nenhum pôde ser carregado."""
    pattern = os.path.join(SESSION_DIR, f"{SESSION_FILE_PREFIX}*")
    for session_path in sorted(glob.glob(pattern)):
        session_username = _session_username_from_path(session_path)
        if not session_username:
            continue
        try:
            L.load_session_from_file(session_username, filename=session_path)
            return session_username
        except Exception:
            continue
    return None


def detect_available_session_username():
    """Detecta (sem carregar cookies) o primeiro arquivo de sessão salvo em
    SESSION_DIR, para feedback de UI (sidebar do Streamlit) sem o custo de
    desserializar a sessão a cada rerun. Retorna o username, ou None se
    nenhum arquivo de sessão foi encontrado."""
    pattern = os.path.join(SESSION_DIR, f"{SESSION_FILE_PREFIX}*")
    for session_path in sorted(glob.glob(pattern)):
        session_username = _session_username_from_path(session_path)
        if session_username:
            return session_username
    return None


def _resolve_profile_via_topsearch(loader, username):
    """Contorno para o bug de schema removido do Instagram: quando
    Profile.from_username() falha porque o endpoint web_profile_info devolve
    o Erro HTTP 400 de "ig_business_category_subvertical has been deleted"
    (confirmado ao vivo contra @silviabraz em 2026-08-12, ver
    docs/issues/ISSUE-0001.md), usa instaloader.TopSearchResults — endpoint
    diferente (web/search/topsearch/) — para achar o id numérico do perfil.
    Com sessão autenticada, o próprio Instaloader completa os metadados pela
    rota GraphQL por doc_id/id numérico (Profile._obtain_metadata quando
    logado), que não passa por web_profile_info e portanto não é afetada por
    este bug.

    Só funciona logado: anônimo também cai em web_profile_info para
    completar metadados, então não adianta tentar. Retorna o Profile
    resolvido, ou None se não achar candidato com username exatamente igual
    ou se o próprio fallback falhar (ex.: topsearch também instável)."""
    if not loader.context.is_logged_in:
        return None
    try:
        results = instaloader.TopSearchResults(loader.context, username)
        for candidate in results.get_profiles():
            if candidate.username.lower() == username.lower():
                candidate.biography  # força completar metadados (rota GraphQL por id)
                return candidate
    except Exception as exc:
        _logger.warning(
            "Fallback via topsearch para '%s' também falhou: %s", username, exc,
        )
    return None


def instaloader_fetch_fn(username, cookies=None, rate_controller=None, on_progress=None):
    # cookies, se fornecido, é o caminho de um arquivo de sessão local salvo
    # previamente via Instaloader.save_session_to_file (login manual único, fora
    # deste código) — evita reautenticar a cada coleta. Quando não fornecido,
    # tenta autodetectar qualquer sessão salva em SESSION_DIR.
    active_controller = rate_controller or rate_controller_module.NULL_RATE_CONTROLLER

    loader = instaloader.Instaloader()
    if cookies:
        session_username = _session_username_from_path(cookies) or username
        loader.load_session_from_file(session_username, filename=cookies)
    else:
        load_any_available_session(loader)

    active_controller.next_wait("resolucao_inicial")

    try:
        profile = instaloader.Profile.from_username(loader.context, username)
    except instaloader.exceptions.TooManyRequestsException:
        _logger.error(
            "Coleta de '%s' interrompida: Instagram sinalizou 429 (rate limit) ao "
            "resolver o perfil.", username,
        )
        active_controller.observe_response(status_code=429)
        raise
    except (
        instaloader.exceptions.ConnectionException,
        instaloader.exceptions.QueryReturnedBadRequestException,
    ) as exc:
        # QueryReturnedBadRequestException (HTTP 400) é levantada direto por
        # InstaloaderContext.get_json() e NÃO é subclasse de ConnectionException
        # (confirmado lendo instaloadercontext.py: o except que faz retry/wrap só
        # cobre ConnectionException) — é essa a exceção real que o bug de schema
        # removido do Instagram produz. Reproduzido ao vivo contra @silviabraz em
        # 2026-08-12: um `except ConnectionException` sozinho nunca capturava esse
        # erro, e a coleta caía no `except Exception` genérico logo abaixo, pulando
        # o fallback via topsearch por completo.
        if _DELETED_SCHEMA_SIGNATURE in str(exc).lower():
            fallback_profile = _resolve_profile_via_topsearch(loader, username)
            if fallback_profile is None:
                _logger.error(
                    "Coleta de '%s' falhou: Instagram devolveu um erro de schema removido "
                    "no endpoint web_profile_info — bug atual no backend do Instagram, não "
                    "é falha de sessão/autenticação local. Fallback via topsearch também "
                    "não resolveu o perfil. Detalhe: %s", username, exc,
                )
                raise ScraperUnavailableError(
                    f"Instagram recusou a resolução do perfil '{username}' com um erro de "
                    f"schema removido no endpoint web_profile_info (bug atual no backend "
                    f"do Instagram, não é falha de sessão local), e o fallback via "
                    f"topsearch também não conseguiu resolver o perfil: {exc}"
                ) from exc
            _logger.warning(
                "Coleta de '%s': web_profile_info devolveu o bug de schema removido do "
                "Instagram, mas o fallback via topsearch resolveu o perfil normalmente.",
                username,
            )
            profile = fallback_profile
        elif _is_checkpoint_signal(str(exc)):
            _logger.error(
                "Coleta de '%s' interrompida: sinal de checkpoint/challenge do Instagram "
                "ao resolver o perfil.", username,
            )
            active_controller.observe_response(challenge=True)
            raise
        else:
            _logger.error("Coleta de '%s' falhou ao resolver o perfil (conexão): %s", username, exc)
            raise
    except Exception as exc:
        _logger.error("Coleta de '%s' falhou de forma inesperada ao resolver o perfil: %s", username, exc)
        raise
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_WINDOW_DAYS)
    total_hint = min(getattr(profile, "mediacount", None) or MAX_POSTS_SAFETY_CAP, MAX_POSTS_SAFETY_CAP)

    posts = []
    # get_posts() geralmente retorna do mais recente para o mais antigo, mas o
    # Instagram permite fixar até 3 posts no topo do grid fora dessa ordem —
    # inclusive posts bem antigos (reproduzido ao vivo em @silviabraz: os 3
    # primeiros posts vinham de 2021/2024/2025, escondendo posts reais de agosto de
    # 2026 logo em seguida). Por isso só passamos a "confiar" na ordem cronológica
    # (e parar no primeiro post fora da janela) depois do primeiro post que já caiu
    # dentro da janela — antes disso, um post antigo pode ser só um fixado, não o
    # fim do conteúdo recente. Sem posts fixados, o comportamento é idêntico ao
    # anterior (para no primeiro post fora da janela). O teto de segurança
    # (MAX_POSTS_SAFETY_CAP) segue limitando o pior caso (perfil sem nenhum post
    # dentro da janela).
    past_pinned_zone = False
    posts_iterator = iter(profile.get_posts())
    while True:
        try:
            post = next(posts_iterator)
        except StopIteration:
            break
        except instaloader.exceptions.TooManyRequestsException:
            _logger.error(
                "Coleta de '%s' interrompida durante a paginação de posts: 429 "
                "(rate limit).", username,
            )
            active_controller.observe_response(status_code=429)
            raise
        except instaloader.exceptions.ConnectionException as exc:
            if _is_checkpoint_signal(str(exc)):
                _logger.error(
                    "Coleta de '%s' interrompida durante a paginação de posts: sinal "
                    "de checkpoint/challenge do Instagram.", username,
                )
                active_controller.observe_response(challenge=True)
                raise
            raise

        if len(posts) >= MAX_POSTS_SAFETY_CAP:
            break

        post_date = _post_date_utc(post)
        if past_pinned_zone and post_date < cutoff:
            break
        if post_date < cutoff:
            continue
        past_pinned_zone = True

        active_controller.next_wait("secao_post_metadata")
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
        if on_progress is not None:
            on_progress(len(posts), total_hint)

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
    source=None,
):
    """source="demo"/"real" (opcional): quando informado, um cache gravado com
    origem diferente é ignorado (cache miss), para nunca misturar dado
    fictício do Modo Demonstração com dado real do Instagram para o mesmo
    username. Ver database.get_cached_data."""
    cached = database.get_cached_data(username, window_days, source=source, db_path=db_path)
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
    except rate_controller_module.SafeStop:
        # 429/403/challenge: parar de forma explícita, não degradar
        # silenciosamente para um cache que pode estar desatualizado
        # (FINDER-003 §4.1/§6 — comportamento observável, não evasivo).
        raise
    except Exception as exc:
        fallback = database.get_cached_data(username, window_days=None, source=source, db_path=db_path)
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
        source=source,
        db_path=db_path,
    )
    return database.get_cached_data(username, window_days, source=source, db_path=db_path)
