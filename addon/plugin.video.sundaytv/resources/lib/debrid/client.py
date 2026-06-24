"""Client for the user's personal debrid backend.

Calls GET /resolve and returns a ranked list of playable sources. See docs/debrid-api.md for
the contract. Also builds the final Kodi-playable URL (appending any per-source HTTP headers in
Kodi's ``url|Header=Value`` form).
"""

from urllib.parse import quote

from .. import logger, settings
from ..http import HttpError, get_json


class DebridError(Exception):
    pass


class NotConfigured(DebridError):
    pass


def _auth_headers():
    key = settings.backend_api_key()
    return {"Authorization": "Bearer %s" % key} if key else {}


def resolve(descriptor):
    """Resolve a media descriptor into a ranked list of sources.

    descriptor keys: type ('movie'|'episode'), tmdb_id, imdb_id, title, year, season, episode.
    Returns the (possibly empty) list of source dicts, best first. Honours the max-quality cap.
    """
    base = settings.backend_url()
    if not base:
        raise NotConfigured("backend_url")

    params = {
        "type": descriptor["type"],
        "tmdb": descriptor.get("tmdb_id"),
        "imdb": descriptor.get("imdb_id"),
        "title": descriptor.get("title"),
        "year": descriptor.get("year"),
    }
    if descriptor["type"] == "episode":
        params["season"] = descriptor.get("season")
        params["episode"] = descriptor.get("episode")

    try:
        data = get_json(base + "/resolve", params=params, headers=_auth_headers())
    except HttpError as e:
        logger.error("Debrid resolve failed: %s" % e)
        raise DebridError(str(e))

    sources = (data or {}).get("sources", [])
    return _apply_quality_cap(sources)


def _apply_quality_cap(sources):
    cap = settings.max_quality()
    if not cap:
        return sources
    filtered = [s for s in sources if int(s.get("resolution") or 0) <= cap]
    # If everything is above the cap, fall back to the lowest-resolution source rather than
    # leaving the user with nothing to play.
    if not filtered and sources:
        return [min(sources, key=lambda s: int(s.get("resolution") or 0))]
    return filtered


def playable_url(source):
    """Build the URL handed to Kodi's player, including any required request headers."""
    url = source["url"]
    headers = source.get("headers")
    if headers:
        encoded = "&".join("%s=%s" % (k, quote(str(v), safe="")) for k, v in headers.items())
        return "%s|%s" % (url, encoded)
    return url
