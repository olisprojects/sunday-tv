"""Shared pytest setup: wire the Kodi stubs and the add-on/server onto sys.path."""

import os
import sys

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
ADDON_ROOT = os.path.join(ROOT, "addon", "plugin.video.sundaytv")
SERVER_ROOT = os.path.join(ROOT, "server")
KODI_STUBS = os.path.join(HERE, "kodistubs")

# Kodi stub modules (import xbmc, xbmcgui, ...) must win over anything else.
for path in (KODI_STUBS, ADDON_ROOT, SERVER_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(autouse=True)
def fresh_profile(tmp_path):
    """Give every test an isolated add-on profile dir and clean settings."""
    import xbmcaddon
    import xbmcvfs

    profile = tmp_path / "profile"
    profile.mkdir()
    xbmcvfs.set_profile_base(str(profile))
    xbmcaddon.reset()

    # Reset the per-process My List memo so Trakt state doesn't leak between tests.
    try:
        from resources.lib import library
        library._invalidate()
    except Exception:
        pass

    yield
    xbmcaddon.reset()
