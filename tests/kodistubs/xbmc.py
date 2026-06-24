"""Minimal xbmc stub for off-device tests."""

LOGDEBUG = 0
LOGINFO = 1
LOGWARNING = 2
LOGERROR = 3

_LOG = []


def log(msg, level=LOGINFO):
    _LOG.append((level, msg))


def executebuiltin(command, wait=False):
    _LOG.append(("builtin", command))


class Monitor:
    def __init__(self):
        self._aborted = False

    def waitForAbort(self, timeout=0):
        return True  # tests don't loop; signal "abort" so monitor loops exit immediately

    def abortRequested(self):
        return False


class Player:
    def __init__(self):
        self._playing = False
        self.played = None

    def play(self, url=None, listitem=None):
        self.played = (url, listitem)
        self._playing = True

    def isPlaying(self):
        return self._playing

    def getTime(self):
        return 0.0

    def getTotalTime(self):
        return 0.0

    def seekTime(self, seconds):
        pass
