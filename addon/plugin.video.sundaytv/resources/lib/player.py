"""Playback: resolve a title via the personal debrid backend, then play and track progress.

Uses a direct xbmc.Player().play() plus an in-process monitor loop so we can reliably record
resume points (powering Continue Watching) without needing a separate service add-on.
"""

import xbmc
import xbmcgui

from . import context, logger, settings
from .debrid import client as debrid
from .store import progress
from .ui.listing import _apply_infotag

S = settings.get_string


def _descriptor(item):
    """Build the resolve descriptor the backend expects from a normalized item."""
    if item.get("media_type") == "episode":
        return {
            "type": "episode",
            "tmdb_id": item.get("show_tmdb_id"),
            "imdb_id": item.get("show_imdb_id"),
            "title": item.get("show_title"),
            "year": None,
            "season": item.get("season"),
            "episode": item.get("episode"),
        }
    return {
        "type": "movie",
        "tmdb_id": item.get("tmdb_id"),
        "imdb_id": item.get("imdb_id"),
        "title": item.get("title"),
        "year": item.get("year"),
    }


def _choose_source(sources):
    if settings.autoplay():
        return sources[0]
    labels = [s.get("label", s.get("quality", "?")) for s in sources]
    idx = xbmcgui.Dialog().select(S(31015), labels)
    if idx < 0:
        return None
    return sources[idx]


def _maybe_resume(item):
    """Return the start position in seconds (0 = from beginning, None = cancelled)."""
    state = progress.get(item)
    if state["watched"] or not state["position"]:
        return 0
    mins = int(state["position"] // 60)
    secs = int(state["position"] % 60)
    choices = [S(31019).format("%02d:%02d" % (mins, secs)), S(31020)]
    idx = xbmcgui.Dialog().contextmenu(choices)
    if idx < 0:
        return None
    return state["position"] if idx == 0 else 0


def _build_play_item(item, source):
    li = xbmcgui.ListItem(label=item.get("title", ""), path=debrid.playable_url(source))
    li.setArt({
        "poster": item["art"].get("poster", ""),
        "fanart": item["art"].get("fanart", ""),
        "thumb": item["art"].get("thumb", ""),
    })
    _apply_infotag(li, item)
    return li


def play(item):
    """Resolve and play a normalized media item, tracking progress until it stops."""
    dialog = xbmcgui.Dialog()

    if not settings.backend_configured():
        dialog.notification("Sunday TV", S(31016), xbmcgui.NOTIFICATION_WARNING)
        settings.open_settings()
        return

    try:
        sources = debrid.resolve(_descriptor(item))
    except debrid.NotConfigured:
        dialog.notification("Sunday TV", S(31016), xbmcgui.NOTIFICATION_WARNING)
        settings.open_settings()
        return
    except debrid.DebridError as e:
        logger.error("resolve failed: %s" % e)
        dialog.notification("Sunday TV", S(31014), xbmcgui.NOTIFICATION_ERROR)
        return

    if not sources:
        dialog.notification("Sunday TV", S(31014), xbmcgui.NOTIFICATION_INFO)
        return

    source = _choose_source(sources)
    if not source:
        return

    start_at = _maybe_resume(item)
    if start_at is None:
        return

    li = _build_play_item(item, source)
    player = xbmc.Player()
    player.play(debrid.playable_url(source), li)
    _monitor(player, item, start_at)


def _monitor(player, item, start_at):
    """Wait for playback, seek to resume point, then record progress until it stops."""
    monitor = xbmc.Monitor()

    # Wait (up to ~30s) for playback to actually begin.
    waited = 0
    while not player.isPlaying() and waited < 30:
        if monitor.waitForAbort(0.5):
            return
        waited += 0.5
    if not player.isPlaying():
        logger.error("playback never started")
        return

    if start_at and start_at > 0:
        try:
            player.seekTime(float(start_at))
        except Exception:
            pass

    last_pos, last_total = float(start_at or 0), 0.0
    while player.isPlaying() and not monitor.abortRequested():
        try:
            last_pos = player.getTime()
            last_total = player.getTotalTime()
        except Exception:
            pass
        if monitor.waitForAbort(2):
            break

    if last_total > 0:
        progress.save(item, last_pos, last_total)
