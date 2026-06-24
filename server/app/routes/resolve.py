"""GET /resolve — the endpoint the Sunday TV add-on calls when the user presses Play."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db, resolver
from ..auth import require_auth
from ..models import MediaType, ResolveQuery, ResolveResponse

router = APIRouter()


@router.get("/resolve", response_model=ResolveResponse, dependencies=[Depends(require_auth)])
def resolve(
    type: MediaType = Query(..., description="movie or episode"),
    tmdb: Optional[int] = Query(None),
    imdb: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    episode: Optional[int] = Query(None),
    title: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
) -> ResolveResponse:
    if tmdb is None and not imdb and not title:
        raise HTTPException(status_code=422, detail="Provide at least one of tmdb, imdb or title.")
    if type == MediaType.episode and (season is None or episode is None):
        raise HTTPException(status_code=422, detail="Episode resolve requires season and episode.")

    query = {
        "type": type.value,
        "tmdb": tmdb,
        "imdb": imdb,
        "season": season,
        "episode": episode,
        "title": title,
        "year": year,
    }
    candidates = db.find_candidates(query)
    sources = resolver.rank(candidates)
    return ResolveResponse(query=ResolveQuery(**query), sources=sources)
