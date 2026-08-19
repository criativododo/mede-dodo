"""Coletor Instaloader — amostragem rápida na janela trimestral (ISSUE-002).

12–15 posts mais recentes / 90 dias, 30–50 comentários por post, pacing
conservador (0.3–0.8s entre posts) e fallback estruturado para o cache SQLite
em 429/checkpoint/login. Referências normativas: SPEC-01-MEDE-DODO.md §3.3 e
legado/src/scraper.py (bugs reais já documentados desta versão do Instaloader
— sessão carregada com o username errado, posts fixados fora de ordem).

Duas resiliências adicionais (homologação real 2026-08-15, ver PROGRESS.md §3):
1. Fallback via GraphQL direto para comentários (`_fetch_comments_via_graphql`)
   — porta o workaround já existente em legado/src/scraper.py para o bug
   sistemático do endpoint de comentários do app iPhone
   (`i.instagram.com/api/v1/media/.../comments/`, "something went wrong" em
   100% dos posts testados contra 2 de 3 perfis reais).
2. Janela estendida (`_collect_extended_window`) — perfis que postam pouco
   podem ter menos de 3 posts nos últimos 90 dias; nesse caso, coleta os
   últimos 12-15 posts mais recentes disponíveis (ignorando a janela) em vez
   de devolver uma auditoria vazia.
"""

import glob
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

import instaloader

from src.features.coleta import database

_logger = logging.getLogger(__name__)

WINDOW_DAYS = 90
POSTS_LIMIT = 15
POSTS_SAFETY_CAP = 60
COMMENTS_PER_POST_MIN = 30
COMMENTS_PER_POST_MAX = 50
COMMENT_SLEEP_MIN_SECONDS = 0.3
COMMENT_SLEEP_MAX_SECONDS = 0.8
# Pacing aplicado somente pelo worker seguro. Em produção, o intervalo é
# deliberadamente longo; testes podem injetar sleep_fn/random_fn.
SAFE_PACING_MIN_SECONDS = float(os.getenv("METRICA_DODO_SAFE_PACING_MIN", "30"))
SAFE_PACING_MAX_SECONDS = float(os.getenv("METRICA_DODO_SAFE_PACING_MAX", "120"))

# Fallback de janela inteligente: perfis com menos que este número de posts
# dentro de WINDOW_DAYS caem para os últimos EXTENDED_POSTS_LIMIT posts mais
# recentes (sem filtro de data), em vez de uma auditoria sem nenhum dado.
MIN_POSTS_IN_WINDOW = 3
EXTENDED_POSTS_LIMIT = 15

SESSION_DIR = os.path.join(os.path.expanduser("~"), ".config", "instaloader")
SESSION_FILE_PREFIX = "session-"
DEFAULT_SESSION_USERNAME = "elafashiomkt"

_MEDIA_TYPE_LABELS = {"GraphImage": "Foto", "GraphVideo": "Reel", "GraphSidecar": "Carrossel"}
_SPONSORED_KEYWORDS = ("#publi", "#publicidade", "#parceria", "#ad", "#sponsored", "#patrocinado")
_CHECKPOINT_SIGNATURES = (
    "checkpoint_required", "challenge_required", "feedback_required",
    "checkpoint", "challenge",
)
_ABORT_DOWNLOAD_EXCEPTION = getattr(instaloader.exceptions, "AbortDownloadException", None)
ProgressCallback = Callable[..., None]

# query_hash da consulta GraphQL legada de comentários de post (mesma usada em
# legado/src/scraper.py) — último recurso quando post.get_comments() falha
# sem coletar nada, contornando o bug do endpoint de comentários do app
# iPhone que o Instaloader usa nativamente para posts com muitos comentários.
# Paginação além da 1ª página não é confiável nesse endpoint legado, então não
# tentamos ir além — uma amostra real de comentários é preferível a zero.
_COMMENTS_GRAPHQL_QUERY_HASH = "97b41c52301f77ce508f55e66d17620e"
_COMMENTS_GRAPHQL_FIRST_PAGE_SIZE = 50


def _session_stop_reason(exc: BaseException) -> tuple[str | None, int | None]:
    text = str(exc).lower()
    if _ABORT_DOWNLOAD_EXCEPTION and isinstance(exc, _ABORT_DOWNLOAD_EXCEPTION):
        return "checkpoint", 403
    if any(signature in text for signature in _CHECKPOINT_SIGNATURES):
        return "checkpoint", 403
    if isinstance(exc, instaloader.exceptions.TooManyRequestsException) or "429" in text or "too many requests" in text:
        return "rate_limit", 429
    if "403" in text or "forbidden" in text:
        return "forbidden", 403
    if isinstance(exc, instaloader.exceptions.LoginRequiredException):
        return "login_required", 401
    return None, None


def _emit_progress(callback: ProgressCallback | None, **payload) -> None:
    if callback is None:
        return
    try:
        callback(**payload)
    except Exception:
        # Telemetria não pode mascarar a causa real do Instagram.
        _logger.exception("Falha ao persistir progresso de coleta")


def _pace_before_network(sleep_fn, random_fn, safe_mode: bool, operation: str) -> None:
    if not safe_mode:
        return
    minimum = max(0.0, SAFE_PACING_MIN_SECONDS)
    maximum = max(minimum, SAFE_PACING_MAX_SECONDS)
    delay = random_fn(minimum, maximum)
    _logger.info("Pacing seguro antes de %s: %.2fs", operation, delay)
    sleep_fn(delay)


class ScraperError(Exception):
    """Erro estruturado de coleta (sem cache disponível como fallback)."""

    def __init__(self, reason: str, status_code: int | None = None):
        self.reason = reason
        self.status_code = status_code
        super().__init__(reason)


def _session_username_from_path(path: str) -> str | None:
    """O dono da sessão vem do nome do arquivo ("session-<usuario>"), nunca do
    perfil sendo analisado — bug real já corrigido em legado/src/scraper.py."""
    basename = os.path.basename(path)
    if basename.startswith(SESSION_FILE_PREFIX):
        return basename[len(SESSION_FILE_PREFIX) :]
    return None


def _load_persisted_session(loader: "instaloader.Instaloader") -> str | None:
    default_path = os.path.join(SESSION_DIR, f"{SESSION_FILE_PREFIX}{DEFAULT_SESSION_USERNAME}")
    if os.path.isfile(default_path):
        try:
            loader.load_session_from_file(DEFAULT_SESSION_USERNAME, filename=default_path)
            return DEFAULT_SESSION_USERNAME
        except Exception as exc:
            _logger.warning("Falha ao carregar sessão padrão '%s': %s", DEFAULT_SESSION_USERNAME, exc)

    pattern = os.path.join(SESSION_DIR, f"{SESSION_FILE_PREFIX}*")
    for session_path in sorted(glob.glob(pattern)):
        session_username = _session_username_from_path(session_path)
        if not session_username:
            continue
        try:
            loader.load_session_from_file(session_username, filename=session_path)
            return session_username
        except Exception:
            continue
    return None


def _post_date_utc(post) -> datetime:
    post_date = post.date_utc
    if post_date.tzinfo is None:
        post_date = post_date.replace(tzinfo=timezone.utc)
    return post_date


def _classify_format(post) -> str:
    try:
        return _MEDIA_TYPE_LABELS.get(post.typename, "Foto")
    except Exception:
        return "Foto"


def _is_sponsored(caption: str | None) -> bool:
    if not caption:
        return False
    lowered = caption.lower()
    return any(keyword in lowered for keyword in _SPONSORED_KEYWORDS)


def _is_checkpoint_signal(exc_text: str) -> bool:
    lowered = exc_text.lower()
    return any(signature in lowered for signature in _CHECKPOINT_SIGNATURES)


def _build_post_entry(post) -> dict:
    post_date = _post_date_utc(post)
    return {
        "post_id": str(post.mediaid),
        "format": _classify_format(post),
        "published_at": post_date.isoformat(),
        "likes": post.likes,
        "comments_count": post.comments,
        "caption": post.caption or "",
        "is_sponsored": _is_sponsored(post.caption),
    }


def _extract_comment_owner_display_name(comment) -> str | None:
    """Extrai o nome de exibição real de quem comentou (para o matching de
    demografia do IBGE ser feito sobre um nome de verdade, não o @handle) —
    só quando já vem de graça no payload já buscado (`iphone_struct`, path
    nativo de `post.get_comments()` para posts com muitos comentários). Nunca
    acessa `comment.owner.full_name` diretamente: em comentários vindos da
    consulta GraphQL clássica isso dispararia uma requisição de rede extra
    por comentarista, inviabilizando o orçamento de <60s da coleta."""
    node = getattr(comment, "_node", None) or {}
    iphone_user = (node.get("iphone_struct") or {}).get("user") or {}
    return iphone_user.get("full_name") or None


def _fetch_comments_via_graphql(post) -> list:
    """Busca só a 1ª página de comentários reais via GraphQL direto — porta
    de `legado/src/scraper.py::_fetch_comments_first_page_via_graphql`, único
    recurso conhecido contra o bug sistemático do endpoint de comentários do
    app iPhone (ver PROGRESS.md §3, homologação real de 2026-08-15)."""
    try:
        data = post._context.graphql_query(
            _COMMENTS_GRAPHQL_QUERY_HASH,
            {"shortcode": post.shortcode, "first": _COMMENTS_GRAPHQL_FIRST_PAGE_SIZE},
        )
        edges = data["data"]["shortcode_media"]["edge_media_to_parent_comment"]["edges"]
    except Exception as exc:
        _logger.warning(
            "Fallback via GraphQL direto para comentários do post %s também falhou: %s",
            getattr(post, "shortcode", "?"), exc,
        )
        return []

    comments = []
    for edge in edges:
        node = edge.get("node") or {}
        owner = node.get("owner") or {}
        comments.append(
            {
                "post_id": str(post.mediaid),
                "username": owner.get("username"),
                "display_name": None,
                "texto": node.get("text"),
            }
        )
    return comments


def _fetch_post_comments(
    post,
    sleep_fn=time.sleep,
    random_fn=random.uniform,
    safe_mode: bool = False,
) -> list:
    limit = int(random_fn(COMMENTS_PER_POST_MIN, COMMENTS_PER_POST_MAX))
    comments = []
    try:
        _pace_before_network(sleep_fn, random_fn, safe_mode, "comentários")
        for comment in post.get_comments():
            if len(comments) >= limit:
                break
            comments.append(
                {
                    "post_id": str(post.mediaid),
                    "username": getattr(getattr(comment, "owner", None), "username", None),
                    "display_name": _extract_comment_owner_display_name(comment),
                    "texto": comment.text,
                }
            )
    except Exception as exc:
        reason, status_code = _session_stop_reason(exc)
        if safe_mode and reason:
            raise ScraperError(reason, status_code=status_code) from exc
        _logger.warning(
            "Falha ao coletar comentários do post %s — mantendo %d já coletado(s): %s",
            getattr(post, "shortcode", "?"), len(comments), exc,
        )

    # Fallback funcional histórico somente para falha sem sinal de proteção;
    # nunca mascara checkpoint, 403 ou 429 do worker seguro.
    if not comments and not safe_mode:
        comments = _fetch_comments_via_graphql(post)[:limit]
        if comments:
            _logger.info(
                "Comentários do post %s recuperados via fallback GraphQL (%d).",
                getattr(post, "shortcode", "?"), len(comments),
            )

    if not safe_mode:
        sleep_fn(random_fn(COMMENT_SLEEP_MIN_SECONDS, COMMENT_SLEEP_MAX_SECONDS))
    return comments


def _collect_extended_window(
    profile,
    sleep_fn,
    random_fn,
    safe_mode: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> tuple:
    """Últimos posts mais recentes, com parada segura e progresso parcial."""
    posts_data = []
    comments_data = []
    inspected = 0
    try:
        for post in profile.get_posts():
            _pace_before_network(sleep_fn, random_fn, safe_mode, "próximo post da janela estendida")
            inspected += 1
            if len(posts_data) >= EXTENDED_POSTS_LIMIT or inspected > POSTS_SAFETY_CAP:
                break
            posts_data.append(_build_post_entry(post))
            comments_data.extend(
                _fetch_post_comments(post, sleep_fn=sleep_fn, random_fn=random_fn, safe_mode=safe_mode)
            )
            _emit_progress(
                progress_callback,
                stage="posts",
                current=len(posts_data),
                total=EXTENDED_POSTS_LIMIT,
                message=f"Coletando {len(posts_data)}/{EXTENDED_POSTS_LIMIT} posts; aguardando intervalo seguro",
                posts_data=posts_data,
                comments_data=comments_data,
            )
    except Exception as exc:
        reason, status_code = _session_stop_reason(exc)
        if safe_mode and reason:
            raise ScraperError(reason, status_code=status_code) from exc
        _logger.warning(
            "Janela estendida interrompida após %d post(s) coletado(s): %s", len(posts_data), exc,
        )
    return posts_data, comments_data


def _fallback_or_raise(
    username: str,
    reason: str,
    status_code,
    exc,
    db_path,
    allow_cache_fallback: bool = True,
):
    _logger.error("Coleta de '%s' falhou (%s): %s", username, reason, exc)
    if allow_cache_fallback:
        cached = database.get_cached_profile(username, db_path=db_path)
        if cached is not None:
            cached["status"] = "cache_fallback"
            cached["source"] = "cache"
            cached["error_reason"] = reason
            return cached
    raise ScraperError(reason, status_code=status_code) from exc


def collect_profile(
    username: str,
    cache_result: bool = True,
    db_path=database.DB_PATH,
    sleep_fn=time.sleep,
    random_fn=random.uniform,
    progress_callback: ProgressCallback | None = None,
    safe_mode: bool = False,
) -> dict:
    """Coleta rápida de `username`: 12–15 posts/90 dias, 30–50 comentários por
    post (com fallback via GraphQL se o endpoint nativo falhar). Perfis com
    menos de `MIN_POSTS_IN_WINDOW` posts na janela caem para os últimos
    `EXTENDED_POSTS_LIMIT` posts mais recentes. Em 429/checkpoint/login, cai
    para o cache (`cache_fallback`) se disponível, senão levanta
    `ScraperError`."""
    clean_username = username.strip().lstrip("@")
    _emit_progress(
        progress_callback,
        stage="perfil",
        current=0,
        total=POSTS_LIMIT,
        message="Preparando sessão segura...",
    )

    loader = instaloader.Instaloader(max_connection_attempts=2)
    _load_persisted_session(loader)

    try:
        _pace_before_network(sleep_fn, random_fn, safe_mode, "perfil")
        profile = instaloader.Profile.from_username(loader.context, clean_username)
    except Exception as exc:
        reason, status_code = _session_stop_reason(exc)
        if reason:
            return _fallback_or_raise(
                clean_username,
                reason,
                status_code,
                exc,
                db_path,
                allow_cache_fallback=not safe_mode,
            )
        return _fallback_or_raise(
            clean_username,
            "unknown_error",
            None,
            exc,
            db_path,
            allow_cache_fallback=not safe_mode,
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    posts_data = []
    comments_data = []
    inspected = 0

    try:
        for post in profile.get_posts():
            _pace_before_network(sleep_fn, random_fn, safe_mode, "próximo post")
            inspected += 1
            if len(posts_data) >= POSTS_LIMIT or inspected > POSTS_SAFETY_CAP:
                break
            post_date = _post_date_utc(post)
            if post_date < cutoff:
                # nunca `break` aqui: posts fixados podem esconder posts recentes.
                continue
            posts_data.append(_build_post_entry(post))
            comments_data.extend(
                _fetch_post_comments(
                    post,
                    sleep_fn=sleep_fn,
                    random_fn=random_fn,
                    safe_mode=safe_mode,
                )
            )
            _emit_progress(
                progress_callback,
                stage="posts",
                current=len(posts_data),
                total=POSTS_LIMIT,
                message=f"Coletando {len(posts_data)}/{POSTS_LIMIT} posts; aguardando intervalo seguro",
                posts_data=posts_data,
                comments_data=comments_data,
            )
    except Exception as exc:
        reason, status_code = _session_stop_reason(exc)
        if safe_mode and reason:
            raise ScraperError(reason, status_code=status_code) from exc
        if reason and not posts_data:
            return _fallback_or_raise(clean_username, reason, status_code, exc, db_path)
        if not posts_data and isinstance(exc, instaloader.exceptions.ConnectionException):
            return _fallback_or_raise(clean_username, "connection_error", None, exc, db_path)
        _logger.warning("Coleta interrompida após %d post(s): %s", len(posts_data), exc)

    warnings = []
    if len(posts_data) < MIN_POSTS_IN_WINDOW:
        extended_posts, extended_comments = _collect_extended_window(
            profile,
            sleep_fn,
            random_fn,
            safe_mode=safe_mode,
            progress_callback=progress_callback,
        )
        if len(extended_posts) > len(posts_data):
            posts_data = extended_posts
            comments_data = extended_comments
            warnings.append(
                f"Janela estendida: analisando os últimos {len(posts_data)} posts mais recentes "
                f"(menos de {MIN_POSTS_IN_WINDOW} posts encontrados nos últimos {WINDOW_DAYS} dias)."
            )

    profile_data = {
        "username": clean_username,
        "bio": profile.biography,
        "followers_count": profile.followers,
    }

    _emit_progress(
        progress_callback,
        stage="coleta_concluida",
        current=len(posts_data),
        total=max(POSTS_LIMIT, len(posts_data)),
        message=f"Coleta concluída: {len(posts_data)} posts e {len(comments_data)} comentários.",
        profile_data=profile_data,
        posts_data=posts_data,
        comments_data=comments_data,
    )

    if cache_result:
        database.save_profile_cache(clean_username, profile_data, posts_data, comments_data, db_path=db_path)

    return {
        "status": "ok",
        "source": "real",
        "profile_data": profile_data,
        "posts_data": posts_data,
        "comments_data": comments_data,
        "warnings": warnings,
    }



def run_collection_worker(
    job_id: str,
    username: str,
    marca_contratante: str,
    db_path=database.DB_PATH,
    sleep_fn=time.sleep,
    random_fn=random.uniform,
) -> None:
    """Executa a coleta segura fora da View e publica estado no SQLite."""
    partial = {"profile_data": {}, "posts_data": [], "comments_data": []}

    def persist_progress(**payload):
        partial["profile_data"] = payload.get("profile_data", partial["profile_data"])
        partial["posts_data"] = payload.get("posts_data", partial["posts_data"])
        partial["comments_data"] = payload.get("comments_data", partial["comments_data"])
        database.update_audit_job_progress(
            job_id,
            stage=payload.get("stage", "posts"),
            current=payload.get("current", len(partial["posts_data"])),
            total=payload.get("total", POSTS_LIMIT),
            message=payload.get("message", "Coleta em andamento..."),
            partial_profile_data=partial["profile_data"],
            partial_posts_data=partial["posts_data"],
            partial_comments_data=partial["comments_data"],
            db_path=db_path,
        )

    try:
        database.update_audit_job(
            job_id,
            db_path=db_path,
            status="running",
            stage="sessao",
            message="Worker iniciado; respeitando pacing conservador.",
        )
        result = collect_profile(
            username,
            cache_result=True,
            db_path=db_path,
            sleep_fn=sleep_fn,
            random_fn=random_fn,
            progress_callback=persist_progress,
            safe_mode=True,
        )
        partial["profile_data"] = result.get("profile_data", partial["profile_data"])
        partial["posts_data"] = result.get("posts_data", partial["posts_data"])
        partial["comments_data"] = result.get("comments_data", partial["comments_data"])
        database.update_audit_job(
            job_id,
            db_path=db_path,
            status="coleta_concluida",
            stage="coleta_concluida",
            progress_current=len(partial["posts_data"]),
            progress_total=max(POSTS_LIMIT, len(partial["posts_data"])),
            message="Coleta concluída; análise aguardando a próxima atualização da View.",
            partial_profile_data=partial["profile_data"],
            partial_posts_data=partial["posts_data"],
            partial_comments_data=partial["comments_data"],
            result=result,
        )
    except ScraperError as exc:
        session_failure = exc.reason in {"checkpoint", "forbidden", "rate_limit", "login_required"}
        database.update_audit_job(
            job_id,
            db_path=db_path,
            status="falha_sessao" if session_failure else "falha",
            stage="falha_sessao" if session_failure else "falha",
            message=(
                "Coleta interrompida imediatamente pela proteção da sessão; nenhum bypass foi tentado."
                if session_failure
                else "Coleta falhou; os dados parciais foram preservados."
            ),
            error_reason=exc.reason,
            partial_profile_data=partial["profile_data"],
            partial_posts_data=partial["posts_data"],
            partial_comments_data=partial["comments_data"],
        )
    except Exception:
        _logger.exception("Worker de coleta %s falhou", job_id)
        database.update_audit_job(
            job_id,
            db_path=db_path,
            status="falha",
            stage="falha",
            message="Falha inesperada; os dados parciais foram preservados.",
            error_reason="worker_error",
            partial_profile_data=partial["profile_data"],
            partial_posts_data=partial["posts_data"],
            partial_comments_data=partial["comments_data"],
        )
