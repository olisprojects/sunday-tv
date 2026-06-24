# Sunday TV

A Kodi video add-on for Amazon Fire Stick (and any Kodi 20 Nexus / 21 Omega device) that lets
you browse movies and TV shows in a **Netflix‑inspired** interface and stream them through
**your own personal debrid service** — no Real Debrid, no third‑party scrapers.

Sunday TV is modelled on the browse‑and‑watch experience of all‑in‑one add‑ons like *The Crew*,
but with one key difference: instead of depending on an external debrid provider to turn links
into playable streams, it talks to a small self‑hosted backend that **you** own and populate
with **trusted links**. You decide what it serves.

> **Content‑neutral by design.** The add‑on ships with **no** hardcoded sources and **no**
> bundled API keys. You supply your own (free) TMDB API key for metadata and point the add‑on
> at your own backend. What links your backend serves, and your right to access them, is your
> responsibility.

---

## What's in this repo

| Path | What it is |
|------|------------|
| `addon/plugin.video.sundaytv/` | The Kodi add‑on (zip this to install). Python 3, zero external add‑on dependencies. |
| `server/` | The **personal debrid backend** — a self‑hostable FastAPI + SQLite service. |
| `docs/` | Architecture, the add‑on ↔ server API contract, and the Fire Stick install guide. |
| `scripts/package_addon.sh` | Builds an installable `plugin.video.sundaytv-x.y.z.zip`. |
| `tests/` | Pytest suite for the backend and the add‑on logic (with mocked Kodi modules). |

## How it fits together

```
  ┌─────────────────────┐     metadata (HTTPS)      ┌──────────────┐
  │   Sunday TV add‑on  │ ────────────────────────▶ │     TMDB     │
  │   (Kodi / Fire TV)  │                            └──────────────┘
  │                     │     resolve(media)         ┌──────────────────────────┐
  │  browse · My List · │ ────────────────────────▶ │  Personal debrid backend │
  │  Continue Watching  │ ◀──────────────────────── │  (your server, FastAPI)  │
  └─────────────────────┘   ranked playable URLs     └──────────────────────────┘
```

1. The add‑on browses movies/TV using **TMDB** (artwork, descriptions, seasons/episodes).
2. When you press Play, it asks **your backend** to `resolve` that title (by TMDB/IMDb id) into
   a ranked list of direct, playable stream URLs.
3. Kodi plays the best (or you pick the quality). Watch state — **My List**, watched flags and
   resume points for **Continue Watching** — is stored locally on the device.

See [`docs/architecture.md`](docs/architecture.md) for the full picture and the play sequence.

## Quick start

### 1. Run the personal debrid backend

```bash
cd server
pip install -r requirements.txt
export SUNDAYTV_API_KEY="choose-a-long-random-key"
python seed.py            # optional: load demo public‑domain entries
uvicorn app.main:app --host 0.0.0.0 --port 8770
```

Or with Docker: `cd server && SUNDAYTV_API_KEY=... docker compose up`.

The API contract lives in [`docs/debrid-api.md`](docs/debrid-api.md). Populate the library with
your own trusted links via `POST /links` (see that doc for examples).

### 2. Install the add‑on on Fire Stick

```bash
./scripts/package_addon.sh          # produces dist/plugin.video.sundaytv-<version>.zip
```

Then sideload the zip onto your Fire Stick and install it in Kodi from
**Add‑ons → Install from zip file**. Full walkthrough (Downloader / adb, "Unknown sources",
settings) in [`docs/install-firestick.md`](docs/install-firestick.md).

### 3. Configure the add‑on

In Kodi, open **Sunday TV → Settings** and set:

- **TMDB API key** — a free key from <https://www.themoviedb.org/settings/api>.
- **Backend URL** — e.g. `http://192.168.1.50:8770`.
- **Backend API key** — the same `SUNDAYTV_API_KEY` you set on the server.
- Quality / autoplay preferences.

## Development

```bash
pip install -r server/requirements.txt -r requirements-dev.txt
pytest                       # backend + add‑on logic (Kodi modules are mocked in tests/)
python -m py_compile $(git ls-files 'addon/**/*.py')
```

## Disclaimer

Sunday TV is a media front‑end. It does not include, host, or scrape any content, and it ships
with no preconfigured sources. You are responsible for the backend you run, the links you add
to it, and for complying with the laws and rights that apply to anything you stream.
