"""Drives the Trakt device-code authorization flow with a Kodi progress dialog."""

import xbmcgui

from .. import logger, settings
from . import client

S = settings.get_string


def authorize():
    dialog = xbmcgui.Dialog()

    if not settings.trakt_client_id() or not settings.trakt_client_secret():
        dialog.ok("Sunday TV", S(31034))  # need client id/secret
        settings.open_settings()
        return

    try:
        device = client.device_code()
    except client.TraktAuthError as e:
        logger.error("Trakt device code failed: %s" % e)
        dialog.notification("Sunday TV", S(31035), xbmcgui.NOTIFICATION_ERROR)
        return

    progress = xbmcgui.DialogProgress()
    progress.create(
        S(31030),
        "%s\n%s: [B]%s[/B]" % (
            device.get("verification_url", "https://trakt.tv/activate"),
            S(31031),
            device.get("user_code", "?"),
        ),
    )

    expires_in = max(1, int(device.get("expires_in", 600)))

    def on_tick(remaining):
        if progress.iscanceled():
            return True
        pct = int(100 * (1 - (remaining / expires_in)))
        progress.update(max(0, min(100, pct)))
        return False

    try:
        ok = client.poll_for_token(device, on_tick=on_tick)
    except client.TraktAuthError as e:
        progress.close()
        logger.error("Trakt authorization failed: %s" % e)
        dialog.notification("Sunday TV", S(31035), xbmcgui.NOTIFICATION_ERROR)
        return

    progress.close()
    if ok:
        dialog.notification("Sunday TV", S(31032), xbmcgui.NOTIFICATION_INFO)


def deauthorize():
    client.clear_tokens()
    xbmcgui.Dialog().notification("Sunday TV", S(31033), xbmcgui.NOTIFICATION_INFO)
