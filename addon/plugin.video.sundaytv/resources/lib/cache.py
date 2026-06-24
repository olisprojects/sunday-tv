"""SQLite TTL cache for TMDB responses, stored in the add-on profile dir.

Keeps browsing snappy and stays well within TMDB rate limits. Values are JSON blobs keyed by
an arbitrary string (typically the request signature).
"""

import json
import sqlite3
import time

from . import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL,
    expires INTEGER NOT NULL
);
"""


def _conn():
    conn = sqlite3.connect(settings.profile_file("cache.db"))
    conn.execute(_SCHEMA)
    return conn


def get(key):
    try:
        with _conn() as conn:
            row = conn.execute(
                "SELECT value, expires FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if not row:
                return None
            value, expires = row
            if expires < int(time.time()):
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
            return json.loads(value)
    except Exception:
        return None


def set(key, value, ttl_seconds):
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
                (key, json.dumps(value), int(time.time()) + int(ttl_seconds)),
            )
    except Exception:
        pass


def clear():
    try:
        with _conn() as conn:
            conn.execute("DELETE FROM cache")
    except Exception:
        pass
