"""Local on-device storage (My List + watch progress), backed by SQLite in the profile dir."""

import sqlite3

from .. import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    key        TEXT PRIMARY KEY,
    media_type TEXT NOT NULL,
    item_json  TEXT NOT NULL,
    added_at   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS progress (
    key        TEXT PRIMARY KEY,
    media_type TEXT NOT NULL,
    item_json  TEXT NOT NULL,
    position   REAL NOT NULL DEFAULT 0,
    total      REAL NOT NULL DEFAULT 0,
    watched    INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);
"""


def connect():
    conn = sqlite3.connect(settings.profile_file("store.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def item_key(item):
    """Stable key for a media item. Episodes are keyed by show + season + episode."""
    if item.get("media_type") == "episode":
        return "episode:%s:s%se%s" % (
            item.get("show_tmdb_id"),
            item.get("season"),
            item.get("episode"),
        )
    return "%s:%s" % (item.get("media_type"), item.get("tmdb_id"))
