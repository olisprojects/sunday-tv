"""Tests for the optional Trakt client and the library facade routing."""

import time

import xbmcaddon


MOVIE = {
    "media_type": "movie", "tmdb_id": 603, "imdb_id": "tt0133093",
    "title": "The Matrix", "year": 1999, "plot": "", "rating": 8.2, "votes": 1,
    "genres": [], "mpaa": "", "duration": 8160, "premiered": "1999-03-31",
    "art": {"poster": "p", "fanart": "f", "thumb": "t", "clearlogo": ""},
}
EPISODE = {
    "media_type": "episode", "show_tmdb_id": 1396, "show_imdb_id": "tt0903747",
    "show_title": "Breaking Bad", "season": 1, "episode": 1,
    "art": {"poster": "p", "fanart": "f", "thumb": "t", "clearlogo": ""},
}


def _enable_trakt():
    xbmcaddon.set_setting("trakt_enabled", True)
    xbmcaddon.set_setting("trakt_client_id", "cid")
    xbmcaddon.set_setting("trakt_client_secret", "secret")


# --------------------------------------------------------------- client tokens
def test_token_storage_round_trip():
    from resources.lib.trakt import client
    assert client.is_authorized() is False
    client._save_tokens({"access_token": "abc", "refresh_token": "r", "expires_at": time.time() + 9999})
    assert client.is_authorized() is True
    client.clear_tokens()
    assert client.is_authorized() is False


def test_payload_grouping():
    from resources.lib.trakt import client
    payload = client._payload_for([MOVIE, EPISODE])
    assert payload["movies"] == [{"ids": {"tmdb": 603}}]
    assert payload["shows"][0]["ids"]["tmdb"] == 1396
    assert payload["shows"][0]["seasons"][0]["episodes"][0]["number"] == 1


def test_device_code_requires_client_id():
    from resources.lib.trakt import client
    xbmcaddon.set_setting("trakt_client_id", "")
    try:
        client.device_code()
        assert False, "expected TraktAuthError"
    except client.TraktAuthError as e:
        assert str(e) == "no_client_id"


def test_watchlist_add_posts_payload(monkeypatch):
    from resources.lib.trakt import client
    _enable_trakt()
    client._save_tokens({"access_token": "abc", "expires_at": time.time() + 9999})
    calls = {}

    def fake_post(url, body=None, headers=None, timeout=20):
        calls["url"] = url
        calls["body"] = body
        calls["auth"] = headers.get("Authorization")
        calls["key"] = headers.get("trakt-api-key")
        return {}

    monkeypatch.setattr(client, "post_json", fake_post)
    client.watchlist_add(MOVIE)
    assert calls["url"].endswith("/sync/watchlist")
    assert calls["body"]["movies"] == [{"ids": {"tmdb": 603}}]
    assert calls["auth"] == "Bearer abc"
    assert calls["key"] == "cid"


def test_request_refreshes_on_401(monkeypatch):
    from resources.lib.trakt import client
    from resources.lib.http import HttpError
    _enable_trakt()
    client._save_tokens({"access_token": "old", "refresh_token": "r", "expires_at": time.time() + 9999})

    state = {"first": True, "refreshed": False}

    def fake_get(url, params=None, headers=None, timeout=20):
        if state["first"]:
            state["first"] = False
            raise HttpError(401, "expired")
        return [{"movie": {"ids": {"tmdb": 603}}}]

    def fake_post(url, body=None, headers=None, timeout=20):
        # the refresh call
        state["refreshed"] = True
        return {"access_token": "new", "refresh_token": "r2", "expires_in": 7776000}

    monkeypatch.setattr(client, "get_json", fake_get)
    monkeypatch.setattr(client, "post_json", fake_post)
    ids = client.watchlist_tmdb_ids()
    assert state["refreshed"] is True
    assert 603 in ids
    assert client._load_tokens()["access_token"] == "new"


# --------------------------------------------------------------- library facade
def test_library_falls_back_to_local_when_trakt_off():
    from resources.lib import library
    from resources.lib.store import watchlist
    # Trakt disabled -> pure local behaviour.
    library.mylist_add(MOVIE)
    assert watchlist.contains(MOVIE)
    assert any(i["tmdb_id"] == 603 for i in library.mylist_items())
    assert library.mylist_contains(MOVIE) is True
    library.mylist_remove(MOVIE)
    assert library.mylist_contains(MOVIE) is False


def test_library_mirrors_to_trakt_when_on(monkeypatch):
    from resources.lib import library
    from resources.lib.trakt import client
    from resources.lib.store import watchlist
    _enable_trakt()
    client._save_tokens({"access_token": "abc", "expires_at": time.time() + 9999})

    sent = []
    monkeypatch.setattr(client, "watchlist_add", lambda item: sent.append(("add", item["tmdb_id"])))
    library.mylist_add(MOVIE)
    # Local is always written too (so we can render offline).
    assert watchlist.contains(MOVIE)
    assert ("add", 603) in sent


def test_library_mylist_reads_from_trakt(monkeypatch):
    from resources.lib import library
    from resources.lib.trakt import client
    _enable_trakt()
    client._save_tokens({"access_token": "abc", "expires_at": time.time() + 9999})

    monkeypatch.setattr(client, "watchlist_items",
                        lambda: [{"media_type": "movie", "tmdb_id": 603}])
    monkeypatch.setattr(library.tmdb, "movie_detail", lambda tid: dict(MOVIE, tmdb_id=tid))
    items = library.mylist_items()
    assert len(items) == 1 and items[0]["tmdb_id"] == 603


def test_library_continue_watching_from_trakt(monkeypatch):
    from resources.lib import library
    from resources.lib.trakt import client
    _enable_trakt()
    client._save_tokens({"access_token": "abc", "expires_at": time.time() + 9999})

    monkeypatch.setattr(client, "playback",
                        lambda: [({"media_type": "movie", "tmdb_id": 603}, 50.0)])
    monkeypatch.setattr(library.tmdb, "movie_detail", lambda tid: dict(MOVIE, tmdb_id=tid, duration=3600))
    cw = library.continue_watching()
    assert len(cw) == 1
    # 50% of a 3600s film -> ~1800s resume point.
    assert abs(cw[0]["_resume"]["position"] - 1800) < 1


def test_library_trakt_error_falls_back(monkeypatch):
    from resources.lib import library
    from resources.lib.trakt import client
    from resources.lib.store import watchlist
    _enable_trakt()
    client._save_tokens({"access_token": "abc", "expires_at": time.time() + 9999})
    watchlist.add(MOVIE)

    def boom():
        raise client.TraktError("network down")

    monkeypatch.setattr(client, "watchlist_items", boom)
    # Should not raise; falls back to the local watchlist.
    items = library.mylist_items()
    assert any(i["tmdb_id"] == 603 for i in items)


def test_set_watched_syncs_history(monkeypatch):
    from resources.lib import library
    from resources.lib.trakt import client
    _enable_trakt()
    client._save_tokens({"access_token": "abc", "expires_at": time.time() + 9999})

    calls = []
    monkeypatch.setattr(client, "add_to_history", lambda item: calls.append("add"))
    monkeypatch.setattr(client, "remove_from_history", lambda item: calls.append("remove"))
    library.set_watched(MOVIE, True)
    library.set_watched(MOVIE, False)
    assert calls == ["add", "remove"]
    assert library.is_watched(MOVIE) is False
