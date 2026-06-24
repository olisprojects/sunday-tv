"""Thin logging wrapper around xbmc.log."""

import xbmc

_PREFIX = "[plugin.video.sundaytv] "


def info(msg):
    xbmc.log(_PREFIX + str(msg), xbmc.LOGINFO)


def debug(msg):
    xbmc.log(_PREFIX + str(msg), xbmc.LOGDEBUG)


def error(msg):
    xbmc.log(_PREFIX + str(msg), xbmc.LOGERROR)
