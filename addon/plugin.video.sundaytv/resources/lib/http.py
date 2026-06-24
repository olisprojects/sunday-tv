"""A tiny JSON-over-HTTP client built on the Python standard library.

Kept dependency-free (no script.module.requests) so the add-on installs from a zip without
needing any repository. Used by both the TMDB and personal-debrid clients.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import logger

DEFAULT_TIMEOUT = 20


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__("HTTP %s: %s" % (status, message))
        self.status = status
        self.message = message


def _request(method, url, params=None, headers=None, body=None, timeout=DEFAULT_TIMEOUT):
    if params:
        url = url + ("&" if "?" in url else "?") + urlencode(
            {k: v for k, v in params.items() if v is not None}
        )
    data = None
    req_headers = {"Accept": "application/json", "User-Agent": "SundayTV/1.0"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            pass
        logger.error("HTTP %s on %s: %s" % (e.code, url, detail[:200]))
        raise HttpError(e.code, detail)
    except (URLError, OSError) as e:
        logger.error("Network error on %s: %s" % (url, e))
        raise HttpError(0, str(e))
    except ValueError as e:  # JSON decode
        logger.error("Bad JSON from %s: %s" % (url, e))
        raise HttpError(0, "invalid JSON response")


def get_json(url, params=None, headers=None, timeout=DEFAULT_TIMEOUT):
    return _request("GET", url, params=params, headers=headers, timeout=timeout)


def post_json(url, body=None, headers=None, timeout=DEFAULT_TIMEOUT):
    return _request("POST", url, headers=headers, body=body, timeout=timeout)
