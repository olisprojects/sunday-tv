# Sunday TV — Personal Debrid Backend

A small self-hostable service that stores your **trusted links** and resolves a movie/TV title
into a ranked list of directly playable stream URLs. It is the Sunday TV add-on's replacement
for an external debrid provider — **you** own and populate it.

- **Stack:** FastAPI + SQLite (stdlib `sqlite3`), Python 3.
- **Storage:** a single `sundaytv.db` file.
- **Auth:** one bearer token (`SUNDAYTV_API_KEY`), shared with the add-on.
- **Contract:** [`../docs/debrid-api.md`](../docs/debrid-api.md).

## Run it

```bash
pip install -r requirements.txt
export SUNDAYTV_API_KEY="choose-a-long-random-key"
python seed.py                                   # optional demo data (public-domain films)
uvicorn app.main:app --host 0.0.0.0 --port 8770
```

Interactive API docs are then at <http://localhost:8770/docs>.

### Docker

```bash
export SUNDAYTV_API_KEY="choose-a-long-random-key"
docker compose up --build
```

The DB persists in the `sundaytv-data` volume.

## Add your own trusted links

The library is empty until you populate it. Each entry maps a title (by TMDB/IMDb id) to one
playable URL at a given quality. Add as many qualities/sources per title as you like — the
add-on auto-picks the best or shows a picker.

```bash
KEY="choose-a-long-random-key"

# A movie (use the movie's TMDB or IMDb id):
curl -X POST http://localhost:8770/links \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{
        "media_type": "movie",
        "tmdb_id": 603, "imdb_id": "tt0133093",
        "title": "The Matrix", "year": 1999,
        "url": "https://media.example.lan/the-matrix-1080p.mkv",
        "resolution": 1080, "size_bytes": 4402341123,
        "source": "home-nas", "container": "mkv"
      }'

# A TV episode (use the SHOW's id, plus season/episode):
curl -X POST http://localhost:8770/links \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{
        "media_type": "episode",
        "tmdb_id": 1396, "imdb_id": "tt0903747",
        "title": "Breaking Bad",
        "season": 1, "episode": 1,
        "url": "https://media.example.lan/bb-s01e01-1080p.mkv",
        "resolution": 1080, "source": "home-nas", "container": "mkv"
      }'

# List / delete:
curl -H "Authorization: Bearer $KEY" http://localhost:8770/links
curl -X DELETE -H "Authorization: Bearer $KEY" http://localhost:8770/links/7
```

## Tests

From the repo root:

```bash
pip install -r server/requirements.txt -r requirements-dev.txt
pytest tests/test_backend.py
```

## Notes

- Bind to `0.0.0.0` (not `127.0.0.1`) so the Fire Stick can reach it over the LAN, and use the
  server's LAN IP in the add-on's **Backend URL** setting.
- If `SUNDAYTV_API_KEY` is unset, the server refuses all authed requests (fail-closed).
- The `headers` field on a link lets you attach HTTP headers (e.g. an auth token) that Kodi
  will send when fetching that URL.
