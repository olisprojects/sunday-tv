"""SQLite storage for the personal debrid backend.

A single ``links`` table holds every trusted link. We keep the layer deliberately small and
dependency-free (stdlib ``sqlite3``) so the service is trivial to self-host.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

DB_PATH = os.environ.get("SUNDAYTV_DB", os.path.join(os.path.dirname(__file__), "..", "sundaytv.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type  TEXT    NOT NULL,
    tmdb_id     INTEGER,
    imdb_id     TEXT,
    title       TEXT,
    year        INTEGER,
    season      INTEGER,
    episode     INTEGER,
    url         TEXT    NOT NULL,
    resolution  INTEGER NOT NULL DEFAULT 0,
    size_bytes  INTEGER,
    source      TEXT    NOT NULL DEFAULT 'personal',
    container   TEXT    NOT NULL DEFAULT 'mp4',
    headers     TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_links_tmdb ON links(media_type, tmdb_id, season, episode);
CREATE INDEX IF NOT EXISTS idx_links_imdb ON links(media_type, imdb_id, season, episode);
"""


def _connect(path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(path: Optional[str] = None) -> None:
    with _connect(path) as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def get_conn(path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d.pop("created_at", None)
    headers = d.get("headers")
    d["headers"] = json.loads(headers) if headers else None
    return d


def insert_link(data: Dict[str, Any], path: Optional[str] = None) -> Dict[str, Any]:
    headers = data.get("headers")
    with get_conn(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO links
                (media_type, tmdb_id, imdb_id, title, year, season, episode,
                 url, resolution, size_bytes, source, container, headers)
            VALUES (:media_type, :tmdb_id, :imdb_id, :title, :year, :season, :episode,
                    :url, :resolution, :size_bytes, :source, :container, :headers)
            """,
            {
                "media_type": data["media_type"],
                "tmdb_id": data.get("tmdb_id"),
                "imdb_id": data.get("imdb_id"),
                "title": data.get("title"),
                "year": data.get("year"),
                "season": data.get("season"),
                "episode": data.get("episode"),
                "url": data["url"],
                "resolution": data.get("resolution", 0),
                "size_bytes": data.get("size_bytes"),
                "source": data.get("source", "personal"),
                "container": data.get("container", "mp4"),
                "headers": json.dumps(headers) if headers else None,
            },
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM links WHERE id = ?", (new_id,)).fetchone()
        return _row_to_dict(row)


def delete_link(link_id: int, path: Optional[str] = None) -> bool:
    with get_conn(path) as conn:
        cur = conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
        return cur.rowcount > 0


def list_links(
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    offset: int = 0,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    filters = filters or {}
    where, params = _build_where(filters)
    with get_conn(path) as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM links {where}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT * FROM links {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return {"total": total, "items": [_row_to_dict(r) for r in rows]}


def find_candidates(query: Dict[str, Any], path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all links that could match a resolve query (id match, then title fallback)."""
    media_type = query["type"]
    with get_conn(path) as conn:
        # Primary: exact id match (tmdb or imdb), with season/episode for episodes.
        id_clauses = []
        params: List[Any] = [media_type]
        if query.get("tmdb") is not None:
            id_clauses.append("tmdb_id = ?")
            params.append(query["tmdb"])
        if query.get("imdb"):
            id_clauses.append("imdb_id = ?")
            params.append(query["imdb"])

        rows: List[sqlite3.Row] = []
        if id_clauses:
            sql = f"SELECT * FROM links WHERE media_type = ? AND ({' OR '.join(id_clauses)})"
            if media_type == "episode":
                sql += " AND season = ? AND episode = ?"
                params += [query.get("season"), query.get("episode")]
            rows = conn.execute(sql, params).fetchall()

        # Fallback: loose title (+year) match when nothing matched by id.
        if not rows and query.get("title"):
            sql = "SELECT * FROM links WHERE media_type = ? AND title LIKE ? COLLATE NOCASE"
            fparams: List[Any] = [media_type, f"%{query['title']}%"]
            if query.get("year"):
                sql += " AND (year = ? OR year IS NULL)"
                fparams.append(query["year"])
            if media_type == "episode":
                sql += " AND season = ? AND episode = ?"
                fparams += [query.get("season"), query.get("episode")]
            rows = conn.execute(sql, fparams).fetchall()

        return [_row_to_dict(r) for r in rows]


def count_links(path: Optional[str] = None) -> int:
    with get_conn(path) as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM links").fetchone()["c"]


def _build_where(filters: Dict[str, Any]) -> tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []
    for col in ("media_type", "tmdb_id", "imdb_id", "season", "episode"):
        if filters.get(col) is not None:
            clauses.append(f"{col} = ?")
            params.append(filters[col])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params
