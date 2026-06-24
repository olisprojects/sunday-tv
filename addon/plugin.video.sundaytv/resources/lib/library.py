"""Library facade: My List, watched state, and resume points.

Chooses between optional Trakt sync and local on-device storage. Local storage is always
written (so we have full item dicts to render and a working offline fallback); when Trakt is
enabled and authorized, operations are additionally mirrored to / read from Trakt so the user's
library follows them across devices.

All Trakt calls are best-effort: any TraktError is logged and we fall back to local behaviour
rather than breaking navigation.
"""

from . import logger, settings
from .metadata import tmdb
from .store import progress, watchlist
from .trakt import client as trakt

# Per-invocation memo (each Kodi plugin call is a fresh process) so we don't hit Trakt once per
# rendered list item when checking My List membership.
_wl_ids_cache = None


def _trakt_on():
    return settings.trakt_enabled() and trakt.is_authorized()


def _invalidate():
    global _wl_ids_cache
    _wl_ids_cache = None


# --------------------------------------------------------------------- My List
def mylist_add(item):
    watchlist.add(item)
    if _trakt_on():
        try:
            trakt.watchlist_add(item)
            _invalidate()
        except trakt.TraktError as e:
            logger.error("Trakt watchlist add failed: %s" % e)


def mylist_remove(item):
    watchlist.remove(item)
    if _trakt_on():
        try:
            trakt.watchlist_remove(item)
            _invalidate()
        except trakt.TraktError as e:
            logger.error("Trakt watchlist remove failed: %s" % e)


def mylist_contains(item):
    if _trakt_on():
        global _wl_ids_cache
        try:
            if _wl_ids_cache is None:
                _wl_ids_cache = trakt.watchlist_tmdb_ids()
            return item.get("tmdb_id") in _wl_ids_cache
        except trakt.TraktError as e:
            logger.error("Trakt watchlist check failed: %s" % e)
    return watchlist.contains(item)


def mylist_items():
    if _trakt_on():
        try:
            items = [_enrich(stub) for stub in trakt.watchlist_items()]
            return [i for i in items if i]
        except trakt.TraktError as e:
            logger.error("Trakt watchlist fetch failed: %s" % e)
    return watchlist.list_items()


# -------------------------------------------------------------- Watched state
def is_watched(item):
    return progress.get(item)["watched"]


def set_watched(item, watched):
    progress.set_watched(item, watched)
    if _trakt_on():
        try:
            if watched:
                trakt.add_to_history(item)
            else:
                trakt.remove_from_history(item)
        except trakt.TraktError as e:
            logger.error("Trakt history update failed: %s" % e)


# ------------------------------------------------------------ Continue Watching
def continue_watching():
    if _trakt_on():
        try:
            out = []
            for stub, pct in trakt.playback():
                item = _enrich(stub)
                if not item:
                    continue
                total = float(item.get("duration") or 0)
                position = (pct / 100.0) * total if total else 0.0
                item["_resume"] = {"position": position, "total": total}
                out.append(item)
            return out
        except trakt.TraktError as e:
            logger.error("Trakt playback fetch failed: %s" % e)
    return progress.continue_watching()


def save_progress(item, position, total):
    progress.save(item, position, total)
    if _trakt_on() and settings.trakt_scrobble() and total:
        try:
            trakt.scrobble(item, position / total * 100.0, action="stop")
        except trakt.TraktError as e:
            logger.error("Trakt scrobble failed: %s" % e)


# ------------------------------------------------------------------- helpers
def _enrich(stub):
    """Turn a Trakt stub ({media_type, tmdb_id[, season, episode]}) into a full TMDB item."""
    try:
        mt = stub.get("media_type")
        if mt == "movie":
            return tmdb.movie_detail(stub["tmdb_id"])
        if mt == "tv":
            return tmdb.tv_detail(stub["tmdb_id"])
        if mt == "episode":
            return tmdb.episode_detail(stub["show_tmdb_id"], stub["season"], stub["episode"])
    except Exception as e:  # TMDB/network hiccup shouldn't drop the whole row
        logger.error("Could not enrich Trakt item %s: %s" % (stub, e))
    return None
