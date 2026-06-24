"""Sunday TV — Kodi add-on entry point.

Kodi invokes this script with three argv entries:
    argv[0] = the plugin base URL  (plugin://plugin.video.sundaytv/)
    argv[1] = the plugin handle    (int)
    argv[2] = the query string      (?action=...)

We hand those straight to the router, which dispatches to the right screen.
"""

import sys

from resources.lib.router import Router


if __name__ == "__main__":
    Router(sys.argv).dispatch()
