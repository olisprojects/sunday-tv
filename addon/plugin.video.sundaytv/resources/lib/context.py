"""Per-invocation plugin context: base URL, handle, and URL building.

Set once at the start of dispatch from sys.argv, then used everywhere to build plugin:// URLs
and to address the current directory handle.
"""

from urllib.parse import parse_qsl, urlencode

BASE_URL = None
HANDLE = -1


def init(argv):
    global BASE_URL, HANDLE
    BASE_URL = argv[0]
    HANDLE = int(argv[1]) if len(argv) > 1 and argv[1].lstrip("-").isdigit() else -1


def url(**kwargs):
    query = {k: v for k, v in kwargs.items() if v is not None}
    return "%s?%s" % (BASE_URL, urlencode(query))


def parse(query_string):
    return dict(parse_qsl((query_string or "").lstrip("?")))
