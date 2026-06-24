"""Watch progress: resume points + watched flags, powering Continue Watching."""

import json
import time

from . import connect, item_key

# Below this fraction watched we treat playback as "just started" (don't surface a resume).
MIN_RESUME_FRACTION = 0.02
# At/after this fraction we consider the item finished and mark it watched.
WATCHED_FRACTION = 0.90


def save(item, position, total):
    """Record playback position. Auto-marks watched when near the end."""
    key = item_key(item)
    position = max(0.0, float(position or 0))
    total = max(0.0, float(total or 0))
    watched = 1 if (total > 0 and position / total >= WATCHED_FRACTION) else 0
    if watched:
        position = 0.0  # finished — no resume point
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO progress "
            "(key, media_type, item_json, position, total, watched, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (key, item.get("media_type"), json.dumps(item), position, total, watched, int(time.time())),
        )


def get(item):
    key = item_key(item)
    with connect() as conn:
        row = conn.execute(
            "SELECT position, total, watched FROM progress WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return {"position": 0.0, "total": 0.0, "watched": False}
        return {
            "position": row["position"],
            "total": row["total"],
            "watched": bool(row["watched"]),
        }


def set_watched(item, watched=True):
    key = item_key(item)
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO progress "
            "(key, media_type, item_json, position, total, watched, updated_at) "
            "VALUES (?, ?, ?, COALESCE((SELECT position FROM progress WHERE key = ?), 0), "
            "COALESCE((SELECT total FROM progress WHERE key = ?), 0), ?, ?)",
            (key, item.get("media_type"), json.dumps(item), key, key,
             1 if watched else 0, int(time.time())),
        )
        if watched:
            conn.execute("UPDATE progress SET position = 0 WHERE key = ?", (key,))


def continue_watching():
    """Items that are partway through (not finished), most-recently-played first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT item_json, position, total FROM progress "
            "WHERE watched = 0 AND total > 0 AND position / total >= ? "
            "ORDER BY updated_at DESC LIMIT 30",
            (MIN_RESUME_FRACTION,),
        ).fetchall()
        out = []
        for r in rows:
            item = json.loads(r["item_json"])
            item["_resume"] = {"position": r["position"], "total": r["total"]}
            out.append(item)
        return out
