"""Minimal xbmcplugin stub for off-device tests. Records directory operations."""

SORT_METHOD_NONE = 0
SORT_METHOD_LABEL = 1

# Recorded state, inspectable by tests.
added_items = []
content_type = None
ended = []


def reset():
    global content_type
    added_items.clear()
    ended.clear()
    content_type = None


def setContent(handle, content):
    global content_type
    content_type = content


def addDirectoryItem(handle, url, listitem, isFolder=False, totalItems=0):
    added_items.append({"url": url, "listitem": listitem, "isFolder": isFolder})
    return True


def addSortMethod(handle, sortMethod, label2Mask=""):
    pass


def endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True):
    ended.append(succeeded)


def setResolvedUrl(handle, succeeded, listitem):
    ended.append(("resolved", succeeded))
