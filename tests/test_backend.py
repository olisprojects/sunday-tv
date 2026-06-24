"""Tests for the personal debrid backend: auth, resolve ranking, library CRUD."""

import importlib
import os

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SUNDAYTV_API_KEY", "secret")
    monkeypatch.setenv("SUNDAYTV_DB", str(tmp_path / "test.db"))
    # Re-import the app fresh so it binds to this test's DB path.
    import app.db as db
    import app.main as main
    importlib.reload(db)
    importlib.reload(main)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


AUTH = {"Authorization": "Bearer secret"}


def _movie(**over):
    base = {
        "media_type": "movie",
        "tmdb_id": 603,
        "imdb_id": "tt0133093",
        "title": "The Matrix",
        "year": 1999,
        "url": "http://nas/matrix-1080.mkv",
        "resolution": 1080,
        "size_bytes": 4_000_000_000,
        "source": "nas",
        "container": "mkv",
    }
    base.update(over)
    return base


def test_health_no_auth(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_auth_required(client):
    assert client.get("/links").status_code == 401
    assert client.get("/resolve", params={"type": "movie", "tmdb": 603}).status_code == 401
    assert client.get("/links", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_add_and_resolve_ranks_best_first(client):
    client.post("/links", headers=AUTH, json=_movie(url="http://nas/1080.mkv", resolution=1080,
                                                    size_bytes=4_000_000_000))
    client.post("/links", headers=AUTH, json=_movie(url="http://nas/4k.mkv", resolution=2160,
                                                    size_bytes=18_000_000_000))
    r = client.get("/resolve", headers=AUTH, params={"type": "movie", "tmdb": 603})
    assert r.status_code == 200
    sources = r.json()["sources"]
    assert [s["resolution"] for s in sources] == [2160, 1080]
    assert sources[0]["quality"] == "4K"
    assert "GB" in sources[0]["label"]


def test_resolve_by_imdb(client):
    client.post("/links", headers=AUTH, json=_movie())
    r = client.get("/resolve", headers=AUTH, params={"type": "movie", "imdb": "tt0133093"})
    assert len(r.json()["sources"]) == 1


def test_episode_season_matching(client):
    ep = {
        "media_type": "episode", "tmdb_id": 1396, "title": "Breaking Bad",
        "season": 1, "episode": 1, "url": "http://nas/bb-s01e01.mkv",
        "resolution": 1080, "source": "nas", "container": "mkv",
    }
    client.post("/links", headers=AUTH, json=ep)
    hit = client.get("/resolve", headers=AUTH,
                     params={"type": "episode", "tmdb": 1396, "season": 1, "episode": 1})
    assert len(hit.json()["sources"]) == 1
    miss = client.get("/resolve", headers=AUTH,
                      params={"type": "episode", "tmdb": 1396, "season": 2, "episode": 1})
    assert miss.json()["sources"] == []


def test_episode_requires_season_episode(client):
    r = client.get("/resolve", headers=AUTH, params={"type": "episode", "tmdb": 1396})
    assert r.status_code == 422


def test_resolve_requires_an_identifier(client):
    r = client.get("/resolve", headers=AUTH, params={"type": "movie"})
    assert r.status_code == 422


def test_title_fallback_when_no_id_match(client):
    client.post("/links", headers=AUTH, json=_movie(tmdb_id=None, imdb_id=None))
    r = client.get("/resolve", headers=AUTH,
                   params={"type": "movie", "tmdb": 999, "title": "Matrix", "year": 1999})
    assert len(r.json()["sources"]) == 1


def test_link_crud(client):
    created = client.post("/links", headers=AUTH, json=_movie()).json()
    link_id = created["id"]
    assert client.get("/links", headers=AUTH).json()["total"] == 1
    assert client.delete(f"/links/{link_id}", headers=AUTH).status_code == 204
    assert client.delete(f"/links/{link_id}", headers=AUTH).status_code == 404
    assert client.get("/links", headers=AUTH).json()["total"] == 0


def test_headers_round_trip_into_source(client):
    client.post("/links", headers=AUTH, json=_movie(headers={"Authorization": "Bearer x"}))
    r = client.get("/resolve", headers=AUTH, params={"type": "movie", "tmdb": 603})
    assert r.json()["sources"][0]["headers"] == {"Authorization": "Bearer x"}


def test_fail_closed_without_server_key(tmp_path, monkeypatch):
    monkeypatch.delenv("SUNDAYTV_API_KEY", raising=False)
    monkeypatch.setenv("SUNDAYTV_DB", str(tmp_path / "k.db"))
    import app.db as db
    import app.main as main
    importlib.reload(db)
    importlib.reload(main)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        # No configured key -> authed endpoints refuse (503), even with a bearer token.
        assert c.get("/links", headers={"Authorization": "Bearer anything"}).status_code == 503
