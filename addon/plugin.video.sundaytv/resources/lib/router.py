"""Dispatch plugin:// requests to the right screen or action."""

import json

import xbmc
import xbmcgui
import xbmcplugin

from . import context, library, logger, settings
from .metadata import tmdb
from .metadata.tmdb import image_url
from .ui import listing, menus

S = settings.get_string


class Router:
    def __init__(self, argv):
        context.init(argv)
        self.params = context.parse(argv[2] if len(argv) > 2 else "")

    def dispatch(self):
        action = self.params.get("action")
        try:
            self._route(action)
        except tmdb.TmdbError as e:
            self._tmdb_problem(e)
        except Exception as e:  # never leave Kodi with a spinning directory
            logger.error("Unhandled error in action=%s: %s" % (action, e))
            xbmcgui.Dialog().notification("Sunday TV", str(e), xbmcgui.NOTIFICATION_ERROR)
            if context.HANDLE >= 0:
                xbmcplugin.endOfDirectory(context.HANDLE, succeeded=False)

    # ------------------------------------------------------------------ routing
    def _route(self, action):
        if action in (None, "", "home"):
            return menus.home()
        if action == "row":
            return self._row(self.params.get("row"))
        if action == "movies":
            return menus.movies_menu()
        if action == "tvshows":
            return menus.tvshows_menu()
        if action == "genres":
            return self._genres(self.params.get("media"))
        if action == "genre":
            return self._genre(self.params.get("media"), self.params.get("id"))
        if action == "search":
            return self._search()
        if action == "show":
            return self._show(int(self.params["id"]))
        if action == "season":
            return self._season(int(self.params["id"]), int(self.params["season"]))
        if action == "play":
            return self._play()
        if action == "list_add":
            return self._list_add()
        if action == "list_remove":
            return self._list_remove()
        if action == "toggle_watched":
            return self._toggle_watched()
        if action == "trakt_auth":
            return self._trakt_auth()
        if action == "settings":
            return settings.open_settings()
        logger.error("Unknown action: %s" % action)
        return menus.home()

    # -------------------------------------------------------------------- rows
    def _row(self, row):
        if row == "continue":
            return listing.render(library.continue_watching(), content="movies")
        if row == "mylist":
            return listing.render(library.mylist_items(), content="movies")
        if not self._require_tmdb():
            return
        fetchers = {
            "trending": tmdb.trending,
            "popular_movies": tmdb.popular_movies,
            "popular_tv": tmdb.popular_tv,
            "top_rated_movies": tmdb.top_rated_movies,
            "top_rated_tv": tmdb.top_rated_tv,
        }
        fetch = fetchers.get(row)
        if not fetch:
            return menus.home()
        content = "tvshows" if "tv" in row else "movies"
        return listing.render(fetch(), content=content)

    # ------------------------------------------------------------------ genres
    def _genres(self, media):
        if not self._require_tmdb():
            return
        genre_list = tmdb.tv_genres() if media == "tv" else tmdb.movie_genres()
        return menus.genres(genre_list, media)

    def _genre(self, media, genre_id):
        if not self._require_tmdb():
            return
        if media == "tv":
            return listing.render(tmdb.discover_tv(genre_id), content="tvshows")
        return listing.render(tmdb.discover_movies(genre_id), content="movies")

    # ------------------------------------------------------------------ search
    def _search(self):
        if not self._require_tmdb():
            return
        query = xbmcgui.Dialog().input(S(31018))
        if not query:
            if context.HANDLE >= 0:
                xbmcplugin.endOfDirectory(context.HANDLE, succeeded=False)
            return
        return listing.render(tmdb.search(query), content="movies")

    # ------------------------------------------------------------- tv drilldown
    def _show(self, tmdb_id):
        if not self._require_tmdb():
            return
        show = tmdb.tv_detail(tmdb_id)
        entries = []
        for season in show.get("seasons", []):
            num = season.get("season_number")
            label = season.get("name") or ("Season %s" % num)
            art = {
                "poster": image_url(season.get("poster_path"), "w780") or show["art"].get("poster", ""),
                "fanart": show["art"].get("fanart", ""),
            }
            entries.append((label, context.url(action="season", id=tmdb_id, season=num), art))
        listing.render_folders(entries, content="seasons")

    def _season(self, tmdb_id, season_number):
        if not self._require_tmdb():
            return
        show = tmdb.tv_detail(tmdb_id)
        episodes = tmdb.season_episodes(show, season_number)
        listing.render(episodes, content="episodes")

    # -------------------------------------------------------------------- play
    def _play(self):
        item = self._item_param()
        if not item:
            return
        from . import player  # imported lazily so non-playback actions don't pull in xbmc.Player
        player.play(item)

    # ---------------------------------------------------------- context actions
    def _list_add(self):
        item = self._item_param()
        if item:
            library.mylist_add(item)
            xbmcgui.Dialog().notification("Sunday TV", S(31010), xbmcgui.NOTIFICATION_INFO, 2000)

    def _list_remove(self):
        item = self._item_param()
        if item:
            library.mylist_remove(item)
            xbmc.executebuiltin("Container.Refresh")

    def _toggle_watched(self):
        item = self._item_param()
        if item:
            library.set_watched(item, not library.is_watched(item))
            xbmc.executebuiltin("Container.Refresh")

    def _trakt_auth(self):
        from .trakt import auth as trakt_auth
        trakt_auth.authorize()

    # ------------------------------------------------------------------ helpers
    def _item_param(self):
        raw = self.params.get("item")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            logger.error("Bad item param")
            return None

    def _require_tmdb(self):
        if settings.tmdb_configured():
            return True
        xbmcgui.Dialog().notification("Sunday TV", S(31017), xbmcgui.NOTIFICATION_WARNING)
        settings.open_settings()
        if context.HANDLE >= 0:
            xbmcplugin.endOfDirectory(context.HANDLE, succeeded=False)
        return False

    def _tmdb_problem(self, err):
        if str(err) == "no_api_key":
            self._require_tmdb()
            return
        logger.error("TMDB error: %s" % err)
        xbmcgui.Dialog().notification("Sunday TV", "TMDB error", xbmcgui.NOTIFICATION_ERROR)
        if context.HANDLE >= 0:
            xbmcplugin.endOfDirectory(context.HANDLE, succeeded=False)
