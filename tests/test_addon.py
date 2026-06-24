"""Tests for the Kodi add-on logic, exercised with mocked xbmc modules."""

import xbmcaddon
import xbmcplugin


# --------------------------------------------------------------------- TMDB
def test_normalize_movie():
    from resources.lib.metadata import tmdb
    obj = {
        "id": 603, "title": "The Matrix", "overview": "A hacker learns the truth.",
        "release_date": "1999-03-31", "vote_average": 8.2, "vote_count": 24000,
        "runtime": 136, "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
        "external_ids": {"imdb_id": "tt0133093"},
    }
    item = tmdb.normalize_movie(obj)
    assert item["media_type"] == "movie"
    assert item["tmdb_id"] == 603
    assert item["imdb_id"] == "tt0133093"
    assert item["year"] == 1999
    assert item["duration"] == 136 * 60
    assert item["art"]["poster"].endswith("/p.jpg")
    assert item["art"]["fanart"].endswith("/b.jpg")


def test_normalize_tv_and_episode():
    from resources.lib.metadata import tmdb
    show = tmdb.normalize_tv({
        "id": 1396, "name": "Breaking Bad", "first_air_date": "2008-01-20",
        "overview": "Chemistry teacher.", "poster_path": "/s.jpg", "backdrop_path": "/sb.jpg",
        "external_ids": {"imdb_id": "tt0903747"},
    })
    assert show["media_type"] == "tv"
    assert show["year"] == 2008

    ep = tmdb.normalize_episode(
        {"id": 62085, "name": "Pilot", "season_number": 1, "episode_number": 1,
         "air_date": "2008-01-20", "overview": "...", "still_path": "/still.jpg", "runtime": 58},
        show,
    )
    assert ep["media_type"] == "episode"
    assert ep["season"] == 1 and ep["episode"] == 1
    assert ep["show_tmdb_id"] == 1396
    assert ep["show_imdb_id"] == "tt0903747"
    assert ep["art"]["thumb"].endswith("/still.jpg")


def test_genre_map_applied():
    from resources.lib.metadata import tmdb
    item = tmdb.normalize_movie({"id": 1, "title": "X", "genre_ids": [28, 12]},
                                genre_map={28: "Action", 12: "Adventure"})
    assert item["genres"] == ["Action", "Adventure"]


# -------------------------------------------------------------------- debrid
def test_quality_cap_and_fallback():
    from resources.lib.debrid import client
    sources = [
        {"resolution": 2160, "url": "a"},
        {"resolution": 1080, "url": "b"},
        {"resolution": 720, "url": "c"},
    ]
    xbmcaddon.set_setting("max_quality", 1080)
    capped = client._apply_quality_cap(sources)
    assert [s["resolution"] for s in capped] == [1080, 720]

    xbmcaddon.set_setting("max_quality", 0)
    assert client._apply_quality_cap(sources) == sources

    # Everything above cap -> fall back to the single lowest source.
    xbmcaddon.set_setting("max_quality", 480)
    fb = client._apply_quality_cap(sources)
    assert len(fb) == 1 and fb[0]["resolution"] == 720


def test_playable_url_appends_headers():
    from resources.lib.debrid import client
    plain = client.playable_url({"url": "http://x/v.mkv"})
    assert plain == "http://x/v.mkv"
    withhdr = client.playable_url({"url": "http://x/v.mkv", "headers": {"Authorization": "Bearer a b"}})
    assert withhdr.startswith("http://x/v.mkv|Authorization=Bearer%20a%20b")


def test_resolve_calls_backend(monkeypatch):
    from resources.lib.debrid import client
    from resources.lib import http
    xbmcaddon.set_setting("backend_url", "http://nas:8770")
    xbmcaddon.set_setting("backend_api_key", "k")
    xbmcaddon.set_setting("max_quality", 0)

    captured = {}

    def fake_get_json(url, params=None, headers=None, timeout=20):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return {"sources": [{"resolution": 1080, "url": "http://nas/v.mkv"}]}

    monkeypatch.setattr(client, "get_json", fake_get_json)
    out = client.resolve({"type": "movie", "tmdb_id": 603, "imdb_id": "tt0133093",
                          "title": "The Matrix", "year": 1999})
    assert out[0]["url"] == "http://nas/v.mkv"
    assert captured["url"] == "http://nas:8770/resolve"
    assert captured["params"]["tmdb"] == 603
    assert captured["headers"]["Authorization"] == "Bearer k"


# ------------------------------------------------------------------- stores
def _movie_item():
    return {
        "media_type": "movie", "tmdb_id": 603, "imdb_id": "tt0133093",
        "title": "The Matrix", "year": 1999, "plot": "...", "rating": 8.2, "votes": 1,
        "genres": ["Action"], "mpaa": "R", "duration": 8160, "premiered": "1999-03-31",
        "art": {"poster": "p", "fanart": "f", "thumb": "t", "clearlogo": ""},
    }


def test_watchlist_round_trip():
    from resources.lib.store import watchlist
    item = _movie_item()
    assert not watchlist.contains(item)
    watchlist.add(item)
    assert watchlist.contains(item)
    assert watchlist.list_items()[0]["tmdb_id"] == 603
    watchlist.remove(item)
    assert not watchlist.contains(item)


def test_progress_and_continue_watching():
    from resources.lib.store import progress
    item = _movie_item()
    # 20 minutes into a 60 minute film -> resumable, appears in Continue Watching.
    progress.save(item, 1200, 3600)
    state = progress.get(item)
    assert not state["watched"]
    assert abs(state["position"] - 1200) < 1
    cw = progress.continue_watching()
    assert len(cw) == 1 and cw[0]["_resume"]["position"] == 1200

    # Near the end -> auto-marked watched, drops out of Continue Watching.
    progress.save(item, 3500, 3600)
    assert progress.get(item)["watched"] is True
    assert progress.continue_watching() == []


def test_set_watched_toggle():
    from resources.lib.store import progress
    item = _movie_item()
    progress.set_watched(item, True)
    assert progress.get(item)["watched"] is True
    progress.set_watched(item, False)
    assert progress.get(item)["watched"] is False


# ------------------------------------------------------------------- listing
def test_make_list_item_movie_is_playable():
    from resources.lib.ui import listing
    url, li, is_folder = listing.make_list_item(_movie_item())
    assert is_folder is False
    assert "action=play" in url
    assert li.getVideoInfoTag().data["mediatype"] == "movie"
    assert li.art["poster"] == "p"
    # Has an "Add to My List" context entry.
    assert any("list_add" in entry[1] for entry in li.context_menu)


def test_make_list_item_tv_is_folder():
    from resources.lib.ui import listing
    show = {
        "media_type": "tv", "tmdb_id": 1396, "imdb_id": "tt0903747", "title": "Breaking Bad",
        "year": 2008, "plot": "", "rating": 9.0, "votes": 1, "genres": [], "mpaa": "",
        "duration": 0, "premiered": "2008-01-20",
        "art": {"poster": "p", "fanart": "f", "thumb": "t", "clearlogo": ""},
    }
    url, li, is_folder = listing.make_list_item(show)
    assert is_folder is True
    assert "action=show" in url
    assert li.getVideoInfoTag().data["mediatype"] == "tvshow"


def test_render_writes_directory():
    from resources.lib.ui import listing
    from resources.lib import context
    context.init(["plugin://plugin.video.sundaytv/", "1", ""])
    xbmcplugin.reset()
    listing.render([_movie_item(), _movie_item()], content="movies")
    assert len(xbmcplugin.added_items) == 2
    assert xbmcplugin.content_type == "movies"
    assert xbmcplugin.ended == [True]


# -------------------------------------------------------------------- player
def test_player_descriptor_for_episode():
    from resources.lib import player
    ep = {
        "media_type": "episode", "show_tmdb_id": 1396, "show_imdb_id": "tt0903747",
        "show_title": "Breaking Bad", "season": 1, "episode": 1,
    }
    d = player._descriptor(ep)
    assert d == {"type": "episode", "tmdb_id": 1396, "imdb_id": "tt0903747",
                 "title": "Breaking Bad", "year": None, "season": 1, "episode": 1}


def test_router_builds_and_parses_urls():
    from resources.lib import context
    context.init(["plugin://plugin.video.sundaytv/", "5", ""])
    u = context.url(action="genre", media="movie", id=28)
    assert "action=genre" in u and "media=movie" in u and "id=28" in u
    assert context.parse("?action=genre&id=28") == {"action": "genre", "id": "28"}
