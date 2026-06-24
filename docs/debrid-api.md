# Sunday TV — Personal Debrid API

This is the contract between the **Sunday TV add‑on** (client) and your **personal debrid
backend** (server). The reference backend in [`server/`](../server) implements it exactly; if
you replace the backend with your own, keep this shape and the add‑on will keep working.

The backend's one job: given a piece of media (identified by TMDB/IMDb id, plus season/episode
for TV), return a **ranked list of directly playable stream URLs** ("sources"). It is the
user's own replacement for an external debrid service — it stores trusted links the user
curates and resolves them on request.

## Conventions

- Base URL is configured in the add‑on settings, e.g. `http://192.168.1.50:8770`.
- All endpoints return JSON.
- Authentication: every endpoint except `GET /health` requires a bearer token:

  ```
  Authorization: Bearer <SUNDAYTV_API_KEY>
  ```

  The key is set on the server (env `SUNDAYTV_API_KEY`) and mirrored in the add‑on settings.
- Errors use standard HTTP status codes with a body of `{"detail": "<message>"}`.

## Endpoints

### `GET /health`

Liveness probe. No auth.

```json
200 OK
{ "status": "ok", "name": "sunday-tv-debrid", "version": "1.0.0", "links": 12 }
```

### `GET /resolve`

Resolve a title into ranked playable sources. **This is the endpoint the add‑on calls on
Play.** Auth required.

Query parameters:

| Param     | Type   | Required | Notes |
|-----------|--------|----------|-------|
| `type`    | string | yes      | `movie` or `episode`. |
| `tmdb`    | int    | one of\* | TMDB id of the movie or the **show**. |
| `imdb`    | string | one of\* | IMDb id (e.g. `tt0133093`) of the movie or the **show**. |
| `season`  | int    | for episodes | Season number. |
| `episode` | int    | for episodes | Episode number. |
| `title`   | string | optional | Used as a loose fallback match when no id matches. |
| `year`    | int    | optional | Disambiguates `title` fallback. |

\* At least one of `tmdb` / `imdb` should be supplied. For `type=episode`, `season` and
`episode` are required.

Response:

```json
200 OK
{
  "query": { "type": "movie", "tmdb": 603, "imdb": "tt0133093" },
  "sources": [
    {
      "url": "https://media.example.lan/the-matrix-2160p.mkv",
      "quality": "4K",
      "label": "4K • 18.4 GB • home-nas",
      "resolution": 2160,
      "size_bytes": 19783456789,
      "source": "home-nas",
      "container": "mkv",
      "headers": { "Authorization": "Bearer abc" }
    },
    {
      "url": "https://media.example.lan/the-matrix-1080p.mp4",
      "quality": "1080p",
      "label": "1080p • 4.1 GB • home-nas",
      "resolution": 1080,
      "size_bytes": 4402341123,
      "source": "home-nas",
      "container": "mp4",
      "headers": null
    }
  ]
}
```

`sources` is ordered **best first** (highest resolution, then largest size). The add‑on either
auto‑plays `sources[0]` or shows a picker using each source's `label`. Empty `sources` means
"no streams available" — the add‑on surfaces that to the user.

**Source object fields**

| Field        | Type           | Notes |
|--------------|----------------|-------|
| `url`        | string         | A directly playable URL (Kodi `Player().play`). |
| `quality`    | string         | Human label: `4K`, `1080p`, `720p`, `SD`. |
| `label`      | string         | Full one‑line label for the quality picker. |
| `resolution` | int            | Vertical pixels, used for ranking. |
| `size_bytes` | int \| null    | File size; tie‑breaker for ranking. |
| `source`     | string         | Free‑text origin tag (e.g. `home-nas`). |
| `container`  | string         | `mkv`, `mp4`, … |
| `headers`    | object \| null | Optional HTTP headers Kodi should send when fetching `url` (appended as `|Header=Value`). |

### `POST /links`  (admin)

Add a trusted link to the library. Auth required.

Request body:

```json
{
  "media_type": "movie",
  "tmdb_id": 603,
  "imdb_id": "tt0133093",
  "title": "The Matrix",
  "year": 1999,
  "season": null,
  "episode": null,
  "url": "https://media.example.lan/the-matrix-2160p.mkv",
  "resolution": 2160,
  "size_bytes": 19783456789,
  "source": "home-nas",
  "container": "mkv",
  "headers": null
}
```

For an episode, set `media_type: "episode"`, the **show's** `tmdb_id`/`imdb_id`, and
`season`/`episode`. Response is the stored record including its `id`:

```json
201 Created
{ "id": 7, "media_type": "movie", "tmdb_id": 603, ... }
```

### `GET /links`  (admin)

List stored links. Auth required. Optional filters: `media_type`, `tmdb_id`, `imdb_id`,
`season`, `episode`, plus `limit` (default 100) and `offset`.

```json
200 OK
{ "total": 12, "items": [ { "id": 7, ... }, ... ] }
```

### `DELETE /links/{id}`  (admin)

Remove a stored link. Auth required. `204 No Content` on success, `404` if not found.

## Ranking

The reference resolver matches rows whose ids (and season/episode for TV) equal the query, with
a loose `title`+`year` fallback when no id matches, then ranks **by `resolution` desc, then
`size_bytes` desc**. A custom backend may rank however it likes as long as best is first.
