import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cache.db"


def get_connection(db_path=DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_PATH):
    conn = get_connection(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            bio TEXT,
            followers_count INTEGER,
            updated_at TEXT NOT NULL,
            source TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            post_id TEXT NOT NULL,
            raw_payload TEXT NOT NULL,
            likes_count INTEGER,
            comments_count INTEGER,
            collected_at TEXT NOT NULL,
            UNIQUE(username, post_id)
        )
        """
    )
    # Migração: bancos criados antes da coluna `source` existir não têm essa
    # coluna. Colunas antigas ficam com source=NULL, o que get_cached_data()
    # trata como "origem desconhecida" e nunca casa com um pedido explícito de
    # source="demo" ou source="real" — autocura sem precisar apagar cache antigo.
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(profiles)")}
    if "source" not in existing_columns:
        conn.execute("ALTER TABLE profiles ADD COLUMN source TEXT")
    conn.commit()
    conn.close()


def save_profile_data(username, posts, bio=None, followers_count=None, source=None, db_path=DB_PATH):
    init_db(db_path=db_path)
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO profiles (username, bio, followers_count, updated_at, source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            bio=excluded.bio,
            followers_count=excluded.followers_count,
            updated_at=excluded.updated_at,
            source=excluded.source
        """,
        (username, bio, followers_count, now, source),
    )
    # Remove o snapshot de posts anterior antes de gravar o novo: sem isso,
    # uma raspagem real feita depois de uma raspagem em Modo Demonstração (ou
    # vice-versa) apenas ACRESCENTA posts ao cache existente (post_id de demo
    # nunca colide com post_id real), misturando comentários fictícios e reais
    # na mesma resposta de get_cached_data.
    conn.execute("DELETE FROM posts_cache WHERE username = ?", (username,))
    for post in posts:
        conn.execute(
            """
            INSERT INTO posts_cache (username, post_id, raw_payload, likes_count, comments_count, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username, post_id) DO UPDATE SET
                raw_payload=excluded.raw_payload,
                likes_count=excluded.likes_count,
                comments_count=excluded.comments_count,
                collected_at=excluded.collected_at
            """,
            (
                username,
                post["post_id"],
                json.dumps(post.get("raw", {})),
                post.get("likes_count"),
                post.get("comments_count"),
                now,
            ),
        )
    conn.commit()
    conn.close()


def clear_profile_cache(username, db_path=DB_PATH):
    """Apaga do cache local todo o perfil e posts de `username` (RF: botão
    'Limpar Cache e Re-analisar Perfil'). Sem efeito sobre outros perfis; não
    lança exceção se o username não tiver nada cacheado."""
    init_db(db_path=db_path)
    conn = get_connection(db_path)
    conn.execute("DELETE FROM posts_cache WHERE username = ?", (username,))
    conn.execute("DELETE FROM profiles WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def get_cached_data(username, window_days, source=None, db_path=DB_PATH):
    """source=None (padrão) casa com qualquer origem cacheada (compatibilidade
    retroativa). Quando o chamador informa source="demo" ou source="real", um
    cache gravado com origem diferente (ou origem desconhecida, de antes desta
    coluna existir) é tratado como cache miss — nunca serve dado fictício para
    um pedido real, nem o contrário."""
    init_db(db_path=db_path)
    conn = get_connection(db_path)
    # window_days=None = sem corte de idade: usado pelo fallback do scraper para
    # recuperar qualquer cache salvo, mesmo fora da janela normalmente exigida.
    if window_days is None:
        cutoff = datetime.min.replace(tzinfo=timezone.utc).isoformat()
    else:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    if source is None:
        profile_row = conn.execute(
            "SELECT * FROM profiles WHERE username = ? AND updated_at >= ?",
            (username, cutoff),
        ).fetchone()
    else:
        profile_row = conn.execute(
            "SELECT * FROM profiles WHERE username = ? AND updated_at >= ? AND source = ?",
            (username, cutoff, source),
        ).fetchone()
    if profile_row is None:
        conn.close()
        return None
    post_rows = conn.execute(
        "SELECT * FROM posts_cache WHERE username = ? AND collected_at >= ?",
        (username, cutoff),
    ).fetchall()
    conn.close()
    return {
        "profile": dict(profile_row),
        "posts": [
            {
                "post_id": row["post_id"],
                "raw": json.loads(row["raw_payload"]),
                "likes_count": row["likes_count"],
                "comments_count": row["comments_count"],
                "collected_at": row["collected_at"],
            }
            for row in post_rows
        ],
    }
