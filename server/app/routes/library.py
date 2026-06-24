"""Admin routes for curating the trusted-link library."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import db
from ..auth import require_auth
from ..models import Link, LinkIn, LinkList

router = APIRouter(prefix="/links", dependencies=[Depends(require_auth)])


@router.post("", response_model=Link, status_code=status.HTTP_201_CREATED)
def add_link(link: LinkIn) -> Link:
    stored = db.insert_link(link.model_dump(mode="json"))
    return Link(**stored)


@router.get("", response_model=LinkList)
def get_links(
    media_type: Optional[str] = Query(None),
    tmdb_id: Optional[int] = Query(None),
    imdb_id: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    episode: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> LinkList:
    result = db.list_links(
        filters={
            "media_type": media_type,
            "tmdb_id": tmdb_id,
            "imdb_id": imdb_id,
            "season": season,
            "episode": episode,
        },
        limit=limit,
        offset=offset,
    )
    return LinkList(total=result["total"], items=[Link(**i) for i in result["items"]])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_link(link_id: int) -> Response:
    if not db.delete_link(link_id):
        raise HTTPException(status_code=404, detail=f"Link {link_id} not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
