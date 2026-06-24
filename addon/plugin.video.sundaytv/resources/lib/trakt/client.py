"""Optional Trakt.tv integration.

Provides OAuth device-code authentication and the sync endpoints Sunday TV uses to mirror
My List, watched state, and resume points across devices. Trakt is entirely optional: when it
is disabled or not authorized, the add-on falls back to local on-device storage (see
resources/lib/library.py, which chooses between this client and the local stores).

Credentials: the user registers a free Trakt API application and pastes its client id/secret
into settings — we never ship hardcoded credentials.
"""

import json
import time

from .. import logger, settings
from ..http import HttpError, get_json, post_json

API_BASE = "https://api.trakt.tv"
TOKEN_FILE = "trakt.json"

# Device-flow polling statuses we care about.
_PENDING = 400
_EXPIRED = 410
_DENIED = 418


class TraktError(Exception):
    pass


class TraktAuthError(TraktError):
    pass


# --------------------------------------------------------------------- tokens
def _token_path():
    return settings.profile_file(TOKEN_FILE)


def _load_tokens():
    try:
        with open(_token_path(), "r") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_tokens(tokens):
    try:
        with open(_token_path(), "w") as fh:
            json.dump(tokens, fh)
    except OSError as e:
        logger.error("Could not persist Trakt tokens: %s" % e)


def clear_tokens():
    tokens = _load_tokens()
    if tokens:
        _save_tokens({})


def is_authorized():
    return bool(_load_tokens().get("access_token"))


# --------------------------------------------------------------------- headers
def _base_headers():
    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": settings.trakt_client_id(),
    }


def _auth_headers():
    headers = _base_headers()
    token = _load_tokens().get("access_token")
    if token:
        headers["Authorization"] = "Bearer %s" % token
    return headers


# ----------------------------------------------------------------- device auth
def device_code():
    """Begin device authorization. Returns the dict the UI shows to the user."""
    if not settings.trakt_client_id():
        raise TraktAuthError("no_client_id")
    return post_json(
        API_BASE + "/oauth/device/code",
        body={"client_id": settings.trakt_client_id()},
        headers={"Content-Type": "application/json"},
    )


def poll_for_token(device, on_tick=None):
    """Poll until the user authorizes the device code (or it expires).

    ``device`` is the dict from device_code(). ``on_tick`` (optional) is called each interval
    with the remaining seconds, and may return True to cancel. Returns True on success.
    """
    interval = max(1, int(device.get("interval", 5)))
    expires_in = int(device.get("expires_in", 600))
    deadline = time.time() + expires_in
    body = {
        "code": device["device_code"],
        "client_id": settings.trakt_client_id(),
        "client_secret": settings.trakt_client_secret(),
    }
    while time.time() < deadline:
        if on_tick and on_tick(int(deadline - time.time())):
            return False
        time.sleep(interval)
        try:
            tokens = post_json(
                API_BASE + "/oauth/device/token",
                body=body,
                headers={"Content-Type": "application/json"},
            )
        except HttpError as e:
            if e.status == _PENDING:
                continue
            if e.status in (_EXPIRED, _DENIED):
                raise TraktAuthError("authorization_%s" % e.status)
            if e.status == 429:  # slow down
                time.sleep(interval)
                continue
            raise TraktAuthError(str(e))
        if tokens and tokens.get("access_token"):
            tokens["expires_at"] = int(time.time()) + int(tokens.get("expires_in", 0))
            _save_tokens(tokens)
            return True
    raise TraktAuthError("expired")


def _refresh():
    tokens = _load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise TraktAuthError("not_authorized")
    try:
        new = post_json(
            API_BASE + "/oauth/token",
            body={
                "refresh_token": refresh_token,
                "client_id": settings.trakt_client_id(),
                "client_secret": settings.trakt_client_secret(),
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/json"},
        )
    except HttpError as e:
        raise TraktAuthError("refresh_failed: %s" % e)
    new["expires_at"] = int(time.time()) + int(new.get("expires_in", 0))
    _save_tokens(new)
    return new["access_token"]


def _ensure_fresh():
    tokens = _load_tokens()
    if not tokens.get("access_token"):
        raise TraktAuthError("not_authorized")
    # Refresh a little before actual expiry.
    if tokens.get("expires_at") and tokens["expires_at"] - 600 < int(time.time()):
        _refresh()


# ----------------------------------------------------------------- request core
def _request(method, path, body=None):
    _ensure_fresh()
    url = API_BASE + path
    try:
        if method == "GET":
            return get_json(url, headers=_auth_headers())
        return post_json(url, body=body or {}, headers=_auth_headers())
    except HttpError as e:
        if e.status == 401:
            _refresh()
            if method == "GET":
                return get_json(url, headers=_auth_headers())
            return post_json(url, body=body or {}, headers=_auth_headers())
        raise TraktError(str(e))


# --------------------------------------------------------------- id conversion
def _movie_ref(item):
    return {"ids": {"tmdb": item.get("tmdb_id")}}


def _show_ref(item):
    tmdb_id = item.get("show_tmdb_id") if item.get("media_type") == "episode" else item.get("tmdb_id")
    return {"ids": {"tmdb": tmdb_id}}


def _episode_show_payload(item):
    return {
        "ids": {"tmdb": item.get("show_tmdb_id")},
        "seasons": [
            {"number": item.get("season"), "episodes": [{"number": item.get("episode")}]}
        ],
    }


def _payload_for(items):
    """Group normalized items into a Trakt {movies, shows} sync payload."""
    movies, shows = [], []
    for item in items:
        if item.get("media_type") == "movie":
            movies.append(_movie_ref(item))
        elif item.get("media_type") == "tv":
            shows.append(_show_ref(item))
        elif item.get("media_type") == "episode":
            shows.append(_episode_show_payload(item))
    payload = {}
    if movies:
        payload["movies"] = movies
    if shows:
        payload["shows"] = shows
    return payload


# ----------------------------------------------------------------- sync: list
def watchlist_add(item):
    _request("POST", "/sync/watchlist", _payload_for([item]))


def watchlist_remove(item):
    _request("POST", "/sync/watchlist/remove", _payload_for([item]))


def watchlist_items():
    """Return the watchlist as normalized stubs: [{media_type, tmdb_id}].

    Shows are reported as media_type 'tv'. The library facade enriches each stub via TMDB so it
    can be rendered with full artwork.
    """
    out = []
    movies = _request("GET", "/sync/watchlist/movies") or []
    for entry in movies:
        tmdb_id = (entry.get("movie", {}).get("ids") or {}).get("tmdb")
        if tmdb_id:
            out.append({"media_type": "movie", "tmdb_id": tmdb_id})
    shows = _request("GET", "/sync/watchlist/shows") or []
    for entry in shows:
        tmdb_id = (entry.get("show", {}).get("ids") or {}).get("tmdb")
        if tmdb_id:
            out.append({"media_type": "tv", "tmdb_id": tmdb_id})
    return out


def watchlist_tmdb_ids():
    """Return the set of TMDB ids on the user's watchlist (movies + shows)."""
    return {s["tmdb_id"] for s in watchlist_items()}


# -------------------------------------------------------------- sync: watched
def add_to_history(item):
    _request("POST", "/sync/history", _payload_for([item]))


def remove_from_history(item):
    _request("POST", "/sync/history/remove", _payload_for([item]))


def watched_movie_ids():
    data = _request("GET", "/sync/watched/movies") or []
    return {(e.get("movie", {}).get("ids") or {}).get("tmdb") for e in data}


# ------------------------------------------------------------ sync: playback
def playback():
    """Return in-progress items from Trakt as (item-stub, progress%) tuples.

    The stub carries tmdb ids + season/episode; the library facade enriches it via TMDB for
    rendering.
    """
    data = _request("GET", "/sync/playback") or []
    results = []
    for entry in data:
        progress = entry.get("progress", 0)
        if entry.get("type") == "movie":
            tmdb_id = (entry.get("movie", {}).get("ids") or {}).get("tmdb")
            if tmdb_id:
                results.append(({"media_type": "movie", "tmdb_id": tmdb_id}, progress))
        elif entry.get("type") == "episode":
            show_tmdb = (entry.get("show", {}).get("ids") or {}).get("tmdb")
            ep = entry.get("episode", {})
            if show_tmdb:
                results.append((
                    {
                        "media_type": "episode",
                        "show_tmdb_id": show_tmdb,
                        "season": ep.get("season"),
                        "episode": ep.get("number"),
                    },
                    progress,
                ))
    return results


def scrobble(item, progress_percent, action="stop"):
    """Send a scrobble event (start/pause/stop) so Trakt tracks playback."""
    body = {"progress": max(0.0, min(100.0, float(progress_percent)))}
    if item.get("media_type") == "episode":
        body["show"] = _show_ref(item)
        body["episode"] = {"season": item.get("season"), "number": item.get("episode")}
    else:
        body["movie"] = _movie_ref(item)
    _request("POST", "/scrobble/%s" % action, body)
