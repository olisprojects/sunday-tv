"""Turn stored links into a ranked list of playable sources.

The resolver is intentionally simple: it filters the library down to the rows that match a
query (handled in db.find_candidates) and ranks them best-first. A custom backend can replace
this with anything — as long as the first source is the one the add-on should auto-play.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _quality_label(resolution: int) -> str:
    if resolution >= 2160:
        return "4K"
    if resolution >= 1080:
        return "1080p"
    if resolution >= 720:
        return "720p"
    if resolution > 0:
        return f"{resolution}p"
    return "SD"


def _human_size(size_bytes: int | None) -> str:
    if not size_bytes:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size_bytes} B"


def to_source(link: Dict[str, Any]) -> Dict[str, Any]:
    resolution = int(link.get("resolution") or 0)
    quality = _quality_label(resolution)
    size = link.get("size_bytes")
    label = f"{quality} • {_human_size(size)} • {link.get('source', 'personal')}"
    return {
        "url": link["url"],
        "quality": quality,
        "label": label,
        "resolution": resolution,
        "size_bytes": size,
        "source": link.get("source", "personal"),
        "container": link.get("container", "mp4"),
        "headers": link.get("headers"),
    }


def rank(links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Best first: highest resolution, then largest size."""
    sources = [to_source(link) for link in links]
    sources.sort(
        key=lambda s: (s["resolution"], s["size_bytes"] or 0),
        reverse=True,
    )
    return sources
