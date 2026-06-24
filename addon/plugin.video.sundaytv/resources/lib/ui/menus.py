"""Netflix-style home menu and navigation submenus."""

import xbmcplugin

from .. import context, settings
from . import listing

S = settings.get_string


def home():
    """The Netflix-style landing screen: content rows + browse + search."""
    entries = []

    if settings.row_continue():
        entries.append((S(31000), context.url(action="row", row="continue"), _row_art()))
    if settings.row_mylist():
        entries.append((S(31001), context.url(action="row", row="mylist"), _row_art()))
    if settings.row_trending():
        entries.append((S(31002), context.url(action="row", row="trending"), _row_art()))

    entries.extend([
        (S(31003), context.url(action="row", row="popular_movies"), _row_art()),
        (S(31004), context.url(action="row", row="popular_tv"), _row_art()),
        (S(31005), context.url(action="row", row="top_rated_movies"), _row_art()),
        (S(31006), context.url(action="movies"), _row_art()),
        (S(31007), context.url(action="tvshows"), _row_art()),
        (S(31009), context.url(action="search"), _row_art()),
    ])
    listing.render_folders(entries)


def movies_menu():
    entries = [
        (S(31003), context.url(action="row", row="popular_movies"), None),
        (S(31005), context.url(action="row", row="top_rated_movies"), None),
        (S(31008), context.url(action="genres", media="movie"), None),
        (S(31009), context.url(action="search"), None),
    ]
    listing.render_folders(entries)


def tvshows_menu():
    entries = [
        (S(31004), context.url(action="row", row="popular_tv"), None),
        (S(31005), context.url(action="row", row="top_rated_tv"), None),
        (S(31008), context.url(action="genres", media="tv"), None),
        (S(31009), context.url(action="search"), None),
    ]
    listing.render_folders(entries)


def genres(genre_list, media):
    entries = [
        (g["name"], context.url(action="genre", media=media, id=g["id"]), None)
        for g in genre_list
    ]
    listing.render_folders(entries, content="")


def _row_art():
    return None
