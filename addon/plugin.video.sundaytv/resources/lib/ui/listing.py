"""Turn normalized TMDB items into Kodi ListItems and render directories.

Uses the modern InfoTagVideo API (Kodi 20+) rather than the deprecated ListItem.setInfo dict.
Produces a Netflix-like feel through full artwork (poster / fanart / thumb) and rich metadata,
plus context menus for My List and watched state.
"""

import json

import xbmcgui
import xbmcplugin

from .. import context, library, settings
from ..store import progress


def _encode(item):
    return json.dumps(item, separators=(",", ":"))


def _apply_infotag(li, item):
    tag = li.getVideoInfoTag()
    mt = item.get("media_type")
    tag.setTitle(item.get("title", ""))
    tag.setPlot(item.get("plot", ""))
    if item.get("year"):
        tag.setYear(int(item["year"]))
    if item.get("genres"):
        tag.setGenres(list(item["genres"]))
    if item.get("rating"):
        tag.setRating(float(item["rating"]))
    if item.get("votes"):
        tag.setVotes(int(item["votes"]))
    if item.get("mpaa"):
        tag.setMpaa(item["mpaa"])
    if item.get("duration"):
        tag.setDuration(int(item["duration"]))
    if item.get("premiered"):
        tag.setFirstAired(item["premiered"])

    if mt == "movie":
        tag.setMediaType("movie")
    elif mt == "tv":
        tag.setMediaType("tvshow")
    elif mt == "episode":
        tag.setMediaType("episode")
        if item.get("show_title"):
            tag.setTvShowTitle(item["show_title"])
        if item.get("season") is not None:
            tag.setSeason(int(item["season"]))
        if item.get("episode") is not None:
            tag.setEpisode(int(item["episode"]))


def _apply_watched(li, item):
    state = progress.get(item)
    tag = li.getVideoInfoTag()
    if state["watched"]:
        tag.setPlaycount(1)
    elif state["position"] and state["total"]:
        # Surface a resume point so skins show a progress bar.
        try:
            li.setProperty("ResumeTime", str(state["position"]))
            li.setProperty("TotalTime", str(state["total"]))
        except Exception:
            pass


def _context_menu(item):
    menu = []
    if library.mylist_contains(item):
        menu.append((
            settings.get_string(31011),
            "RunPlugin(%s)" % context.url(action="list_remove", item=_encode(item)),
        ))
    else:
        menu.append((
            settings.get_string(31010),
            "RunPlugin(%s)" % context.url(action="list_add", item=_encode(item)),
        ))
    watched = progress.get(item)["watched"]
    label = settings.get_string(31013 if watched else 31012)
    menu.append((
        label,
        "RunPlugin(%s)" % context.url(action="toggle_watched", item=_encode(item)),
    ))
    return menu


def make_list_item(item):
    """Return (url, ListItem, is_folder) for a normalized media item."""
    li = xbmcgui.ListItem(label=item.get("title", ""))
    li.setArt({
        "poster": item["art"].get("poster", ""),
        "fanart": item["art"].get("fanart", ""),
        "thumb": item["art"].get("thumb", ""),
        "icon": item["art"].get("thumb", ""),
        "clearlogo": item["art"].get("clearlogo", ""),
    })
    _apply_infotag(li, item)
    _apply_watched(li, item)
    li.addContextMenuItems(_context_menu(item))

    mt = item.get("media_type")
    if mt == "tv":
        return context.url(action="show", id=item["tmdb_id"]), li, True

    li.setProperty("IsPlayable", "false")
    target = context.url(action="play", item=_encode(item))
    return target, li, False


def render(items, content="movies"):
    """Render a list of normalized items as a Kodi directory."""
    xbmcplugin.setContent(context.HANDLE, content)
    for item in items:
        url, li, is_folder = make_list_item(item)
        xbmcplugin.addDirectoryItem(context.HANDLE, url, li, is_folder)
    xbmcplugin.addSortMethod(context.HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(context.HANDLE)


def render_folders(entries, content=""):
    """Render plain navigation folders. entries = [(label, url, art_dict|None)]."""
    if content:
        xbmcplugin.setContent(context.HANDLE, content)
    for label, url, art in entries:
        li = xbmcgui.ListItem(label=label)
        if art:
            li.setArt(art)
        li.setProperty("SpecialSort", "")
        xbmcplugin.addDirectoryItem(context.HANDLE, url, li, True)
    xbmcplugin.endOfDirectory(context.HANDLE)
