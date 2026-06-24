"""Sunday TV personal debrid backend — FastAPI application.

Run locally:
    export SUNDAYTV_API_KEY="choose-a-long-random-key"
    uvicorn app.main:app --host 0.0.0.0 --port 8770
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__, db
from .models import Health
from .routes import library, resolve


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Sunday TV — Personal Debrid",
    version=__version__,
    description="Stores trusted links and resolves media into ranked playable sources.",
    lifespan=lifespan,
)

# Also ensure the schema exists at import time (covers the TestClient used without a lifespan
# context and any ad-hoc imports). Cheap and idempotent.
db.init_db()


@app.get("/health", response_model=Health, tags=["meta"])
def health() -> Health:
    return Health(version=__version__, links=db.count_links())


app.include_router(resolve.router, tags=["resolve"])
app.include_router(library.router, tags=["library"])
