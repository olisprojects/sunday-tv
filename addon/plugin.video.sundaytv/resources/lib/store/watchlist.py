"""My List — a simple local watchlist of movies and shows."""

import json
import time

from . import connect, item_key


def add(item):
    key = item_key(item)
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist (key, media_type, item_json, added_at) "
            "VALUES (?, ?, ?, ?)",
            (key, item.get("media_type"), json.dumps(item), int(time.time())),
        )


def remove(item_or_key):
    key = item_or_key if isinstance(item_or_key, str) else item_key(item_or_key)
    with connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE key = ?", (key,))


def contains(item):
    key = item_key(item)
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM watchlist WHERE key = ?", (key,)).fetchone()
        return row is not None


def list_items():
    with connect() as conn:
        rows = conn.execute(
            "SELECT item_json FROM watchlist ORDER BY added_at DESC"
        ).fetchall()
        return [json.loads(r["item_json"]) for r in rows]
