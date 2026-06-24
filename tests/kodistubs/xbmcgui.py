"""Minimal xbmcgui stub for off-device tests."""

NOTIFICATION_INFO = "info"
NOTIFICATION_WARNING = "warning"
NOTIFICATION_ERROR = "error"


class _InfoTag:
    def __init__(self):
        self.data = {}

    def setTitle(self, v): self.data["title"] = v
    def setPlot(self, v): self.data["plot"] = v
    def setYear(self, v): self.data["year"] = v
    def setGenres(self, v): self.data["genres"] = v
    def setRating(self, v): self.data["rating"] = v
    def setVotes(self, v): self.data["votes"] = v
    def setMpaa(self, v): self.data["mpaa"] = v
    def setDuration(self, v): self.data["duration"] = v
    def setFirstAired(self, v): self.data["firstaired"] = v
    def setMediaType(self, v): self.data["mediatype"] = v
    def setTvShowTitle(self, v): self.data["tvshowtitle"] = v
    def setSeason(self, v): self.data["season"] = v
    def setEpisode(self, v): self.data["episode"] = v
    def setPlaycount(self, v): self.data["playcount"] = v


class ListItem:
    def __init__(self, label="", label2="", path=""):
        self.label = label
        self.path = path
        self.art = {}
        self.properties = {}
        self.context_menu = []
        self._tag = _InfoTag()

    def setArt(self, art):
        self.art.update(art)

    def setProperty(self, key, value):
        self.properties[key] = value

    def getProperty(self, key):
        return self.properties.get(key, "")

    def addContextMenuItems(self, items):
        self.context_menu.extend(items)

    def getVideoInfoTag(self):
        return self._tag


class DialogProgress:
    def __init__(self):
        self._canceled = False

    def create(self, heading, message=""):
        pass

    def update(self, percent, message=""):
        pass

    def iscanceled(self):
        return self._canceled

    def close(self):
        pass


class Dialog:
    # Tests monkeypatch these as needed.
    def notification(self, heading, message, icon=NOTIFICATION_INFO, time=5000, sound=True):
        return None

    def select(self, heading, options, **kwargs):
        return 0

    def contextmenu(self, options):
        return 0

    def input(self, heading, **kwargs):
        return ""

    def ok(self, heading, message):
        return True
