"""Minimal xbmcaddon stub. Settings live in a module dict tests can mutate."""

_SETTINGS = {}
_INFO = {"id": "plugin.video.sundaytv", "path": "/tmp/plugin.video.sundaytv", "version": "1.0.0"}


def set_setting(key, value):
    _SETTINGS[key] = value


def reset():
    _SETTINGS.clear()


class Addon:
    def __init__(self, id=None):
        pass

    def getSetting(self, key):
        return str(_SETTINGS.get(key, ""))

    def getSettingBool(self, key):
        val = _SETTINGS.get(key, False)
        if isinstance(val, str):
            return val.lower() == "true"
        return bool(val)

    def getSettingInt(self, key):
        try:
            return int(_SETTINGS.get(key, 0))
        except (TypeError, ValueError):
            return 0

    def getAddonInfo(self, key):
        return _INFO.get(key, "")

    def getLocalizedString(self, string_id):
        return "str(%d)" % string_id

    def openSettings(self):
        pass
