"""TMDB client + normalizers.

Fetches metadata and artwork from TMDB and normalizes it into plain dicts that the UI layer
turns into Kodi ListItems. Responses are cached (cache.py) to keep browsing fast.

The normalized "item" shape used throughout the add-on:

    {
      "media_type": "movie" | "tv" | "episode",
      "tmdb_id": int, "imdb_id": str|None,
      "title": str, "year": int|None, "plot": str,
      "rating": float, "votes": int, "genres": [str], "mpaa": str,
      "duration": int (seconds) | 0, "premiered": "YYYY-MM-DD" | "",
      "art": {"poster":..., "fanart":..., "thumb":..., "clearlogo":...},
      # tv-only context carried on episodes:
      "show_tmdb_id":, "show_imdb_id":, "show_title":, "season":, "episode":,
    }
"""

from .. import cache, logger, settings
from ..http import HttpError, get_json

API_BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p"


class TmdbError(Exception):
    pass


def _ttl():
    return settings.cache_hours() * 3600


def _get(path, params=None):
    api_key = settings.tmdb_api_key()
    if not api_key:
        raise TmdbError("no_api_key")
    params = dict(params or {})
    params["api_key"] = api_key
    params["language"] = settings.tmdb_language()
    cache_key = "tmdb:" + path + ":" + repr(sorted(
        (k, v) for k, v in params.items() if k != "api_key"
    ))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = get_json(API_BASE + path, params=params)
    except HttpError as e:
        logger.error("TMDB request failed: %s" % e)
        raise TmdbError(str(e))
    cache.set(cache_key, data, _ttl())
    return data


def image_url(path, size="w500"):
    if not path:
        return ""
    return "%s/%s%s" % (IMG_BASE, size, path)


# --------------------------------------------------------------------------- art
def _art(obj):
    return {
        "poster": image_url(obj.get("poster_path"), "w780"),
        "fanart": image_url(obj.get("backdrop_path"), "w1280"),
        "thumb": image_url(obj.get("poster_path"), "w500"),
        "clearlogo": "",
    }


def _year(date_str):
    if date_str and len(date_str) >= 4 and date_str[:4].isdigit():
        return int(date_str[:4])
    return None


def _genre_names(obj, genre_map=None):
    if obj.get("genres"):
        return [g["name"] for g in obj["genres"]]
    if genre_map and obj.get("genre_ids"):
        return [genre_map[g] for g in obj["genre_ids"] if g in genre_map]
    return []


# --------------------------------------------------------------------- normalize
def normalize_movie(obj, genre_map=None):
    return {
        "media_type": "movie",
        "tmdb_id": obj.get("id"),
        "imdb_id": (obj.get("external_ids") or {}).get("imdb_id") or obj.get("imdb_id"),
        "title": obj.get("title") or obj.get("original_title") or "",
        "year": _year(obj.get("release_date")),
        "plot": obj.get("overview") or "",
        "rating": float(obj.get("vote_average") or 0.0),
        "votes": int(obj.get("vote_count") or 0),
        "genres": _genre_names(obj, genre_map),
        "mpaa": "",
        "duration": int(obj.get("runtime") or 0) * 60,
        "premiered": obj.get("release_date") or "",
        "art": _art(obj),
    }


def normalize_tv(obj, genre_map=None):
    return {
        "media_type": "tv",
        "tmdb_id": obj.get("id"),
        "imdb_id": (obj.get("external_ids") or {}).get("imdb_id"),
        "title": obj.get("name") or obj.get("original_name") or "",
        "year": _year(obj.get("first_air_date")),
        "plot": obj.get("overview") or "",
        "rating": float(obj.get("vote_average") or 0.0),
        "votes": int(obj.get("vote_count") or 0),
        "genres": _genre_names(obj, genre_map),
        "mpaa": "",
        "duration": 0,
        "premiered": obj.get("first_air_date") or "",
        "art": _art(obj),
        "number_of_seasons": obj.get("number_of_seasons") or 0,
    }


def normalize_episode(obj, show):
    art = {
        "poster": show["art"].get("poster", ""),
        "fanart": show["art"].get("fanart", ""),
        "thumb": image_url(obj.get("still_path"), "w500") or show["art"].get("thumb", ""),
        "clearlogo": "",
    }
    return {
        "media_type": "episode",
        "tmdb_id": obj.get("id"),
        "imdb_id": None,
        "title": obj.get("name") or ("Episode %s" % obj.get("episode_number")),
        "year": _year(obj.get("air_date")),
        "plot": obj.get("overview") or "",
        "rating": float(obj.get("vote_average") or 0.0),
        "votes": int(obj.get("vote_count") or 0),
        "genres": show.get("genres", []),
        "mpaa": "",
        "duration": int(obj.get("runtime") or 0) * 60,
        "premiered": obj.get("air_date") or "",
        "art": art,
        "show_tmdb_id": show["tmdb_id"],
        "show_imdb_id": show.get("imdb_id"),
        "show_title": show["title"],
        "season": obj.get("season_number"),
        "episode": obj.get("episode_number"),
    }


# ------------------------------------------------------------------------ lists
def _movie_genre_map():
    data = _get("/genre/movie/list")
    return {g["id"]: g["name"] for g in data.get("genres", [])}


def _tv_genre_map():
    data = _get("/genre/tv/list")
    return {g["id"]: g["name"] for g in data.get("genres", [])}


def trending():
    data = _get("/trending/all/week")
    out = []
    for obj in data.get("results", []):
        if obj.get("media_type") == "movie":
            out.append(normalize_movie(obj))
        elif obj.get("media_type") == "tv":
            out.append(normalize_tv(obj))
    return out


def popular_movies(page=1):
    gmap = _movie_genre_map()
    data = _get("/movie/popular", {"page": page})
    return [normalize_movie(o, gmap) for o in data.get("results", [])]


def popular_tv(page=1):
    gmap = _tv_genre_map()
    data = _get("/tv/popular", {"page": page})
    return [normalize_tv(o, gmap) for o in data.get("results", [])]


def top_rated_movies(page=1):
    gmap = _movie_genre_map()
    data = _get("/movie/top_rated", {"page": page})
    return [normalize_movie(o, gmap) for o in data.get("results", [])]


def top_rated_tv(page=1):
    gmap = _tv_genre_map()
    data = _get("/tv/top_rated", {"page": page})
    return [normalize_tv(o, gmap) for o in data.get("results", [])]


def movie_genres():
    data = _get("/genre/movie/list")
    return data.get("genres", [])


def tv_genres():
    data = _get("/genre/tv/list")
    return data.get("genres", [])


def discover_movies(genre_id, page=1):
    gmap = _movie_genre_map()
    data = _get("/discover/movie", {"with_genres": genre_id, "page": page, "sort_by": "popularity.desc"})
    return [normalize_movie(o, gmap) for o in data.get("results", [])]


def discover_tv(genre_id, page=1):
    gmap = _tv_genre_map()
    data = _get("/discover/tv", {"with_genres": genre_id, "page": page, "sort_by": "popularity.desc"})
    return [normalize_tv(o, gmap) for o in data.get("results", [])]


def search(query, page=1):
    mgmap = _movie_genre_map()
    tgmap = _tv_genre_map()
    data = _get("/search/multi", {"query": query, "page": page})
    out = []
    for obj in data.get("results", []):
        if obj.get("media_type") == "movie":
            out.append(normalize_movie(obj, mgmap))
        elif obj.get("media_type") == "tv":
            out.append(normalize_tv(obj, tgmap))
    return out


# ----------------------------------------------------------------------- detail
def movie_detail(tmdb_id):
    obj = _get("/movie/%s" % tmdb_id, {"append_to_response": "external_ids,release_dates"})
    item = normalize_movie(obj)
    item["mpaa"] = _us_movie_cert(obj)
    return item


def tv_detail(tmdb_id):
    obj = _get("/tv/%s" % tmdb_id, {"append_to_response": "external_ids,content_ratings"})
    item = normalize_tv(obj)
    item["mpaa"] = _us_tv_cert(obj)
    item["seasons"] = [
        s for s in obj.get("seasons", []) if (s.get("season_number") or 0) >= 1
    ]
    return item


def season_episodes(show_item, season_number):
    obj = _get("/tv/%s/season/%s" % (show_item["tmdb_id"], season_number))
    return [normalize_episode(ep, show_item) for ep in obj.get("episodes", [])]


def _us_movie_cert(obj):
    for entry in (obj.get("release_dates") or {}).get("results", []):
        if entry.get("iso_3166_1") == "US":
            for rd in entry.get("release_dates", []):
                if rd.get("certification"):
                    return rd["certification"]
    return ""


def _us_tv_cert(obj):
    for entry in (obj.get("content_ratings") or {}).get("results", []):
        if entry.get("iso_3166_1") == "US" and entry.get("rating"):
            return entry["rating"]
    return ""
