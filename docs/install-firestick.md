# Installing Sunday TV on an Amazon Fire Stick

This guide covers building the add‑on zip, getting it onto a Fire Stick, installing it in Kodi,
and pointing it at your personal debrid backend.

## Prerequisites

- Kodi **20 (Nexus)** or **21 (Omega)** installed on the Fire Stick.
- Your **personal debrid backend** running and reachable from the Fire Stick (same LAN is
  easiest). See [`../server/README.md`](../server/README.md).
- A free **TMDB API key**: <https://www.themoviedb.org/settings/api>.

## 1. Build the add‑on zip

On your computer, from the repo root:

```bash
./scripts/package_addon.sh
# → dist/plugin.video.sundaytv-<version>.zip
```

(The version is read from `addon/plugin.video.sundaytv/addon.xml`.)

Host the zip somewhere the Fire Stick can reach it — for example a short‑lived web server on
your computer:

```bash
cd dist && python3 -m http.server 8000
# the zip is now at http://<your-computer-ip>:8000/plugin.video.sundaytv-<version>.zip
```

## 2. Allow add‑ons from unknown sources (Kodi)

In Kodi: **Settings → System → Add‑ons → Unknown sources → On**. Accept the warning. This is
required to install any add‑on from a zip.

## 3. Get the zip onto the Fire Stick

Pick whichever is convenient:

**Option A — Downloader app (no computer cable):**
1. Install the **Downloader** app from the Amazon Appstore.
2. In Fire TV **Settings → My Fire TV → Developer options**, enable **Install unknown apps**
   for Downloader.
3. Open Downloader and enter the URL of your hosted zip (from step 1). It downloads to
   `/sdcard/Download/`.

**Option B — adb sideload (from your computer):**
1. Enable **ADB debugging** in Fire TV **Developer options**.
2. `adb connect <firestick-ip>:5555`
3. `adb push dist/plugin.video.sundaytv-<version>.zip /sdcard/Download/`

## 4. Install in Kodi

1. Kodi **Settings → Add‑ons → Install from zip file**.
2. Browse to where the zip landed (e.g. **External storage → Download**) and select it.
3. Wait for the "Sunday TV — Add‑on installed" notification.

## 5. Configure

Open **Add‑ons → Video add‑ons → Sunday TV**. The first launch opens settings (or open it via
the context menu → **Settings**). Set:

| Setting | Value |
|---------|-------|
| **TMDB API key** | your free key from themoviedb.org |
| **Backend URL** | e.g. `http://192.168.1.50:8770` (your backend, reachable from the Stick) |
| **Backend API key** | the `SUNDAYTV_API_KEY` you set on the server |
| **Max quality** | cap playback resolution (e.g. 1080p on a basic Stick) |
| **Autoplay best source** | on = play instantly; off = show a quality picker |

Save, then open Sunday TV. You should see the Netflix‑style home rows (Trending, Popular,
Genres, …). Pressing Play on a title the backend has links for will stream it and add it to
**Continue Watching**.

## Updating

Rebuild the zip with a higher `version` in `addon.xml`, get it onto the Stick, and use
**Install from zip file** again — Kodi upgrades in place and keeps your settings and watch
state.

## Troubleshooting

- **"No streams available"** — your backend has no matching links for that title. Add some via
  `POST /links` (see [`debrid-api.md`](debrid-api.md)). Confirm the Stick can reach the backend:
  open `http://<backend>:<port>/health` in a browser on the same network.
- **Nothing loads / empty rows** — check the TMDB API key in settings. Kodi log:
  `Settings → System → Logging`, then look for `plugin.video.sundaytv` lines.
- **Can't install zip** — "Unknown sources" (step 2) isn't enabled, or the zip is corrupt;
  re‑download.
- **Backend unreachable** — use the LAN IP (not `localhost`) in the Backend URL, and make sure
  the server is bound to `0.0.0.0`, not `127.0.0.1`.
