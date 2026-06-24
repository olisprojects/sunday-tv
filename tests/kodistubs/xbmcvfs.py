"""Minimal xbmcvfs stub. Maps special:// paths into a real temp directory."""

import os
import tempfile

_PROFILE_BASE = os.path.join(tempfile.gettempdir(), "sundaytv-test-profile")


def set_profile_base(path):
    global _PROFILE_BASE
    _PROFILE_BASE = path


def translatePath(path):
    if path.startswith("special://profile/addon_data/"):
        rel = path[len("special://profile/addon_data/"):]
        return os.path.join(_PROFILE_BASE, rel)
    if path.startswith("special://profile/"):
        return os.path.join(_PROFILE_BASE, path[len("special://profile/"):])
    return path


def exists(path):
    return os.path.exists(path)


def mkdirs(path):
    os.makedirs(path, exist_ok=True)
    return True
