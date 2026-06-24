"""Bearer-token auth shared by the admin and resolve routes."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def get_api_key() -> str:
    """The expected API key, read fresh so tests can monkeypatch the env."""
    return os.environ.get("SUNDAYTV_API_KEY", "")


def require_auth(authorization: str = Header(default="")) -> None:
    expected = get_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server has no SUNDAYTV_API_KEY configured; refusing all authed requests.",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
