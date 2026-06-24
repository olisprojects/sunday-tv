# Sunday TV — Architecture

Sunday TV has two independently runnable pieces plus the public metadata provider (TMDB):

1. **The Kodi add‑on** (`addon/plugin.video.sundaytv/`) — the front‑end that runs on the Fire
   Stick. It renders the Netflix‑style browse experience and plays streams.
2. **The personal debrid backend** (`server/`) — a small self‑hosted service that stores the
   user's trusted links and resolves a title into ranked playable URLs.
3. **TMDB** — the source of all movie/TV metadata and artwork. The add‑on talks to TMDB
   directly using the user's own API key.

```
   ┌──────────────────────────── Fire Stick / Kodi ───────────────────────────┐
   │                                                                           │
   │   default.py ──▶ resources/lib/router.py  (action dispatch)              │
   │                        │                                                  │
   │     ┌──────────────────┼───────────────────────────────┐                 │
   │     ▼                  ▼                                ▼                 │
   │  ui/menus.py      metadata/tmdb.py                 debrid/client.py       │
   │  ui/listing.py    (+ cache.py)                     player.py              │
   │     │                  │                                │                 │
   │     ▼                  │                                │                 │
   │  store/watchlist.py    │                                │                 │
   │  store/progress.py     │                                │                 │
   └────────────────────────┼────────────────────────────────┼────────────────┘
                            │ HTTPS                           │ HTTP (LAN)
                            ▼                                 ▼
                       ┌─────────┐                  ┌────────────────────┐
                       │  TMDB   │                  │ personal debrid    │
                       └─────────┘                  │ backend (FastAPI)  │
                                                    │  resolver.py       │
                                                    │  SQLite (links)    │
                                                    └────────────────────┘
```

## Add‑on internals

- **`default.py`** — Kodi entry point. Hands the plugin URL/handle/query string to the router.
- **`router.py`** — parses `plugin://plugin.video.sundaytv/?action=...` and dispatches to the
  right handler. Every screen in the add‑on is an `action`.
- **`settings.py`** — typed accessors over `xbmcaddon` settings (TMDB key, backend URL/key,
  quality cap, autoplay flag, row toggles).
- **`http.py`** — a tiny `urllib`‑based JSON client (GET/POST/DELETE, bearer auth, timeouts).
  Used by both the TMDB and debrid clients. No external add‑on dependencies.
- **`cache.py`** — SQLite TTL cache in the add‑on profile dir, so TMDB browsing is snappy and
  stays within rate limits.
- **`metadata/tmdb.py`** — TMDB client: trending, popular, top‑rated, genres, search, and
  movie/show/season/episode detail, including external ids (IMDb) needed for `resolve`.
- **`ui/menus.py`** — defines the Netflix‑style home rows and the genre lists.
- **`ui/listing.py`** — turns TMDB JSON into Kodi `ListItem`s with full InfoTagVideo metadata
  and artwork (poster / fanart / clearlogo / thumb), plus context menus.
- **`debrid/client.py`** — calls the backend's `GET /resolve` and returns ranked sources.
- **`player.py`** — picks a source (autoplay best or quality dialog), starts playback, and
  records progress.
- **`store/watchlist.py`** — "My List", persisted as SQLite in the profile dir.
- **`store/progress.py`** — resume points and watched flags powering "Continue Watching".

## The Play sequence

```
User presses Play on a movie / episode
        │
        ▼
player.play_media(descriptor)            descriptor = {type, tmdb_id, imdb_id,
        │                                              title, year, season, episode}
        ▼
debrid/client.resolve(descriptor)  ──▶  GET /resolve?type=…&tmdb=…&season=…&episode=…
        │                          ◀──  { sources: [ ranked … ] }
        ▼
no sources? → notify "No streams available"
        │
        ▼
autoplay setting?  ── yes ─▶ pick sources[0]
        │
        └─ no ─▶ Dialog().select(labels) → chosen source
        │
        ▼
xbmc.Player().play(url[+headers], ListItem)
        │
        ▼
on stop / end → store/progress.save(descriptor, position, total)
                → title now appears in "Continue Watching" with a resume point
```

## Why a personal debrid backend

*The Crew* and similar add‑ons scrape links at play time and rely on an **external** debrid
provider (Real Debrid, etc.) to turn those links into fast direct streams. Sunday TV removes
both the scraping and the third‑party dependency:

- **You** run the backend, so there's no external account, subscription, or trust boundary.
- The backend only serves links **you** put in it — "trusted links" you control.
- The add‑on stays content‑neutral: it knows how to *ask* for a stream and *play* it, but it
  has no built‑in idea of where content comes from. That's entirely defined by your backend.

The add‑on talks to the backend through the stable contract in
[`debrid-api.md`](debrid-api.md), so you can rewrite or relocate the backend without touching
the add‑on.

## Data & storage

- **Add‑on profile dir** (`special://profile/addon_data/plugin.video.sundaytv/`): TMDB cache,
  My List, and watch progress — all local SQLite, never leaves the device.
- **Backend**: a single SQLite file (`sundaytv.db`) holding the `links` table.

## Compatibility

- Kodi **20 (Nexus)** and **21 (Omega)**, Python 3. Uses the modern `InfoTagVideo` API
  (`ListItem.getVideoInfoTag()`) rather than the deprecated `setInfo` dict.
- No external add‑on dependencies — only `xbmc.python` 3.0.0 — so the zip installs cleanly
  without adding a repository.
