"""Pydantic schemas for the Sunday TV personal debrid backend.

These mirror the contract in docs/debrid-api.md. The same field names are produced by the
backend and consumed by the Kodi add-on's debrid client, so keep the two in sync.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class MediaType(str, Enum):
    movie = "movie"
    episode = "episode"


class LinkIn(BaseModel):
    """A trusted link being added to the library (POST /links)."""

    media_type: MediaType
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    url: str
    resolution: int = Field(default=0, ge=0, description="Vertical pixels, e.g. 1080.")
    size_bytes: Optional[int] = Field(default=None, ge=0)
    source: str = "personal"
    container: str = "mp4"
    headers: Optional[Dict[str, str]] = None

    @model_validator(mode="after")
    def _check(self) -> "LinkIn":
        if self.tmdb_id is None and self.imdb_id is None and not self.title:
            raise ValueError("at least one of tmdb_id, imdb_id or title is required")
        if self.media_type == MediaType.episode and (self.season is None or self.episode is None):
            raise ValueError("episode links require both season and episode")
        return self


class Link(LinkIn):
    """A stored link, as returned by the API."""

    id: int


class Source(BaseModel):
    """A single playable source returned to the add-on by /resolve."""

    url: str
    quality: str
    label: str
    resolution: int
    size_bytes: Optional[int] = None
    source: str
    container: str
    headers: Optional[Dict[str, str]] = None


class ResolveQuery(BaseModel):
    type: MediaType
    tmdb: Optional[int] = None
    imdb: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    title: Optional[str] = None
    year: Optional[int] = None


class ResolveResponse(BaseModel):
    query: ResolveQuery
    sources: List[Source]


class LinkList(BaseModel):
    total: int
    items: List[Link]


class Health(BaseModel):
    status: str = "ok"
    name: str = "sunday-tv-debrid"
    version: str
    links: int
