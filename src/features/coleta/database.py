from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "cache.db"
DEFAULT_TTL_SECONDS = 86400
JOB_STATUSES = {
    "queued",
    "running",
    "coleta_concluida",
    "analisando",
    "concluido",
    "falha_sessao",
    "falha",
}
_JOB_COLUMNS = {
    "status",
    "stage",
    "progress_current",
    "progress_total",
    "message",
    "error_reason",
    "updated_at_utc",
    "worker_heartbeat_utc",
}


def _normalize_username(username: str) -> str:
    return username.strip().lstrip("@")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_connection(db_path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS profile_cache (
            username TEXT PRIMARY KEY,
            profile_data_json TEXT NOT NULL,
            posts_data_json TEXT NOT NULL,
            comments_data_json TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            ttl_seconds INTEGER NOT NULL DEFAULT 86400
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_jobs (
            job_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            marca_contratante TEXT NOT NULL,
            status TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'fila',
            progress_current INTEGER NOT NULL DEFAULT 0,
            progress_total INTEGER NOT NULL DEFAULT 0,
            message TEXT NOT NULL DEFAULT '',
            partial_profile_data_json TEXT NOT NULL DEFAULT '{}',
            partial_posts_data_json TEXT NOT NULL DEFAULT '[]',
            partial_comments_data_json TEXT NOT NULL DEFAULT '[]',
            result_json TEXT,
            error_reason TEXT,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            worker_heartbeat_utc TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS audit_jobs_one_active_per_username
        ON audit_jobs(username)
        WHERE status IN ('queued', 'running', 'coleta_concluida', 'analisando')
        """
    )
    conn.commit()


def _decode_job(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "job_id": row["job_id"],
        "username": row["username"],
        "marca_contratante": row["marca_contratante"],
        "status": row["status"],
        "stage": row["stage"],
        "progress_current": row["progress_current"],
        "progress_total": row["progress_total"],
        "message": row["message"],
        "partial_profile_data": json.loads(row["partial_profile_data_json"] or "{}"),
        "partial_posts_data": json.loads(row["partial_posts_data_json"] or "[]"),
        "partial_comments_data": json.loads(row["partial_comments_data_json"] or "[]"),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "error_reason": row["error_reason"],
        "created_at_utc": row["created_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
        "worker_heartbeat_utc": row["worker_heartbeat_utc"],
    }


def create_audit_job(username: str, marca_contratante: str, db_path=DB_PATH) -> dict:
    clean_username = _normalize_username(username)
    now = _now_utc()
    job_id = uuid.uuid4().hex
    conn = _get_connection(db_path)
    try:
        _init_db(conn)
        try:
            conn.execute(
                """
                INSERT INTO audit_jobs (
                    job_id, username, marca_contratante, status, stage,
                    progress_current, progress_total, message,
                    created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, 'queued', 'fila', 0, 0, ?, ?, ?)
                """,
                (job_id, clean_username, marca_contratante, "Aguardando coleta segura...", now, now),
            )
        except sqlite3.IntegrityError:
            row = conn.execute(
                """
                SELECT * FROM audit_jobs
                WHERE username = ? AND status IN ('queued', 'running', 'coleta_concluida', 'analisando')
                ORDER BY created_at_utc DESC LIMIT 1
                """,
                (clean_username,),
            ).fetchone()
            return _decode_job(row)
        conn.commit()
        row = conn.execute("SELECT * FROM audit_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return _decode_job(row)
    finally:
        conn.close()


def get_audit_job(job_id: str, db_path=DB_PATH) -> dict | None:
    conn = _get_connection(db_path)
    try:
        _init_db(conn)
        row = conn.execute("SELECT * FROM audit_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return _decode_job(row)
    finally:
        conn.close()


def update_audit_job(job_id: str, db_path=DB_PATH, **fields) -> dict | None:
    unknown = set(fields) - (_JOB_COLUMNS | {"result", "partial_profile_data", "partial_posts_data", "partial_comments_data"})
    if unknown:
        raise ValueError(f"Campos de job desconhecidos: {sorted(unknown)}")
    if "status" in fields and fields["status"] not in JOB_STATUSES:
        raise ValueError(f"Status de job inválido: {fields['status']}")

    encoded = {}
    for key, value in fields.items():
        column = {
            "result": "result_json",
            "partial_profile_data": "partial_profile_data_json",
            "partial_posts_data": "partial_posts_data_json",
            "partial_comments_data": "partial_comments_data_json",
        }.get(key, key)
        if key in {"result", "partial_profile_data", "partial_posts_data", "partial_comments_data"}:
            encoded[column] = json.dumps(value or ({} if key == "partial_profile_data" else []))
        else:
            encoded[column] = value
    encoded.setdefault("updated_at_utc", _now_utc())
    encoded.setdefault("worker_heartbeat_utc", encoded["updated_at_utc"])

    assignments = ", ".join(f"{column} = ?" for column in encoded)
    values = list(encoded.values()) + [job_id]
    conn = _get_connection(db_path)
    try:
        _init_db(conn)
        conn.execute(f"UPDATE audit_jobs SET {assignments} WHERE job_id = ?", values)
        conn.commit()
        row = conn.execute("SELECT * FROM audit_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return _decode_job(row)
    finally:
        conn.close()


def update_audit_job_progress(
    job_id: str,
    stage: str,
    current: int,
    total: int,
    message: str,
    partial_profile_data: dict | None = None,
    partial_posts_data: list | None = None,
    partial_comments_data: list | None = None,
    db_path=DB_PATH,
) -> dict | None:
    fields = {
        "status": "running",
        "stage": stage,
        "progress_current": max(0, int(current)),
        "progress_total": max(0, int(total)),
        "message": message,
    }
    if partial_profile_data is not None:
        fields["partial_profile_data"] = partial_profile_data
    if partial_posts_data is not None:
        fields["partial_posts_data"] = partial_posts_data
    if partial_comments_data is not None:
        fields["partial_comments_data"] = partial_comments_data
    return update_audit_job(job_id, db_path=db_path, **fields)


def save_profile_cache(
    username: str,
    profile_data: dict,
    posts_data: list,
    comments_data: list,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    db_path=DB_PATH,
) -> None:
    """Grava (ou sobrescreve) o snapshot completo de cache do perfil."""
    clean_username = _normalize_username(username)
    conn = _get_connection(db_path)
    try:
        _init_db(conn)
        conn.execute(
            """
            INSERT INTO profile_cache (
                username, profile_data_json, posts_data_json, comments_data_json,
                created_at_utc, ttl_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                profile_data_json=excluded.profile_data_json,
                posts_data_json=excluded.posts_data_json,
                comments_data_json=excluded.comments_data_json,
                created_at_utc=excluded.created_at_utc,
                ttl_seconds=excluded.ttl_seconds
            """,
            (
                clean_username,
                json.dumps(profile_data),
                json.dumps(posts_data),
                json.dumps(comments_data),
                _now_utc(),
                ttl_seconds,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_profile(username: str, db_path=DB_PATH) -> dict | None:
    """Retorna o snapshot cacheado de `username` se existir e ainda estiver
    dentro do TTL; caso contrário (ausente ou expirado), retorna `None`."""
    clean_username = _normalize_username(username)
    conn = _get_connection(db_path)
    try:
        _init_db(conn)
        row = conn.execute(
            "SELECT * FROM profile_cache WHERE username = ?", (clean_username,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    created_at = datetime.fromisoformat(row["created_at_utc"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
    if age_seconds >= row["ttl_seconds"]:
        return None

    return {
        "username": clean_username,
        "profile_data": json.loads(row["profile_data_json"]),
        "posts_data": json.loads(row["posts_data_json"]),
        "comments_data": json.loads(row["comments_data_json"]),
        "created_at_utc": row["created_at_utc"],
        "ttl_seconds": row["ttl_seconds"],
        "age_seconds": age_seconds,
    }
