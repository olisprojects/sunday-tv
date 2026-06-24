"""Seed the library with a few public-domain demo entries.

This lets you test the full add-on → backend → playback loop without curating anything first.
Every URL here is a freely-distributable public-domain film hosted by the Internet Archive, so
the demo is content-neutral and legal to stream. Replace/extend with your own trusted links.

Usage:
    python seed.py
"""

from __future__ import annotations

from app import db

# (TMDB id, IMDb id, title, year, resolution, url, container)
DEMO_MOVIES = [
    (
        3653,
        "tt0051744",
        "Night of the Living Dead",  # NB: 1968 cut, public domain
        1968,
        720,
        "https://archive.org/download/night_of_the_living_dead/night_of_the_living_dead_512kb.mp4",
        "mp4",
    ),
    (
        653,
        "tt0017136",
        "Metropolis",
        1927,
        720,
        "https://archive.org/download/Metropolis_201708/Metropolis.mp4",
        "mp4",
    ),
    (
        980,
        "tt0025878",
        "The Man Who Knew Too Much",
        1934,
        480,
        "https://archive.org/download/the_man_who_knew_too_much/the_man_who_knew_too_much_512kb.mp4",
        "mp4",
    ),
]


def main() -> None:
    db.init_db()
    added = 0
    for tmdb_id, imdb_id, title, year, resolution, url, container in DEMO_MOVIES:
        existing = db.list_links(filters={"tmdb_id": tmdb_id})
        if existing["total"]:
            continue
        db.insert_link(
            {
                "media_type": "movie",
                "tmdb_id": tmdb_id,
                "imdb_id": imdb_id,
                "title": title,
                "year": year,
                "url": url,
                "resolution": resolution,
                "size_bytes": None,
                "source": "internet-archive (demo)",
                "container": container,
                "headers": None,
            }
        )
        added += 1
    print(f"Seed complete. Added {added} demo entries. Library now has {db.count_links()} links.")


if __name__ == "__main__":
    main()
