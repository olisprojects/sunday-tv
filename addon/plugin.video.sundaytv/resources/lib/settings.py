"""Typed access to add-on settings and profile paths.

Wraps xbmcaddon so the rest of the code never touches Kodi settings APIs directly. All values
have sensible fallbacks so a freshly-installed add-on doesn't crash before configuration.
"""

import os

import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_PATH = ADDON.getAddonInfo("path")


def _s(key, default=""):
    try:
        value = ADDON.getSetting(key)
    except Exception:
        value = ""
    return value if value not in (None, "") else default


def _b(key, default=False):
    try:
        return ADDON.getSettingBool(key)
    except Exception:
        return default


def _i(key, default=0):
    try:
        return ADDON.getSettingInt(key)
    except Exception:
        return default


# --- Backend (personal debrid) ---
def backend_url():
    return _s("backend_url").rstrip("/")


def backend_api_key():
    return _s("backend_api_key")


def backend_configured():
    return bool(backend_url())


# --- TMDB ---
def tmdb_api_key():
    return _s("tmdb_api_key")


def tmdb_language():
    return _s("tmdb_language", "en-US")


def tmdb_configured():
    return bool(tmdb_api_key())


def cache_hours():
    return _i("cache_hours", 12)


# --- Playback ---
def autoplay():
    return _b("autoplay", True)


def max_quality():
    """0 means unlimited; otherwise a vertical-resolution cap."""
    return _i("max_quality", 0)


# --- Home rows ---
def row_continue():
    return _b("row_continue", True)


def row_mylist():
    return _b("row_mylist", True)


def row_trending():
    return _b("row_trending", True)


# --- Misc ---
def get_string(string_id):
    return ADDON.getLocalizedString(string_id)


def open_settings():
    ADDON.openSettings()


def profile_dir():
    path = xbmcvfs.translatePath("special://profile/addon_data/%s/" % ADDON_ID)
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    return path


def profile_file(name):
    return os.path.join(profile_dir(), name)
