"""Parallel Science API — FastAPI entry point (papers + reviews)."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import get_connection, get_last_synced, init_db, refresh_db
from app.models import HealthResponse
from app.routers import authors, categories, citations, papers, reviews, stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger(__name__)


async def _periodic_refresh(settings) -> None:
    """Background task to refresh both DBs from GCS periodically."""
    interval = settings.db_refresh_interval_minutes * 60
    while True:
        await asyncio.sleep(interval)
        for key, url in (
            ("papers", settings.gcs_db_url),
            ("reviews", settings.reviews_gcs_db_url),
        ):
            try:
                log.info("Periodic %s DB refresh starting", key)
                refresh_db(key, url)
            except Exception:
                log.exception("Periodic %s DB refresh failed", key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db("papers", settings.db_path, settings.gcs_db_url)
    init_db("reviews", settings.reviews_db_path, settings.reviews_gcs_db_url)
    task = asyncio.create_task(_periodic_refresh(settings))
    yield
    task.cancel()


app = FastAPI(
    title="Parallel Science API",
    description=(
        "REST API for the Parallel Science ecosystem — AI-generated research "
        "papers (papers.parallelscience.org) and their Skepthical peer reviews "
        "(reviews.parallelscience.org)."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

prefix = get_settings().api_v1_prefix
app.include_router(papers.router, prefix=prefix)
app.include_router(authors.router, prefix=prefix)
app.include_router(categories.router, prefix=prefix)
app.include_router(citations.router, prefix=prefix)
app.include_router(reviews.router, prefix=prefix)
app.include_router(stats.router, prefix=prefix)


@app.get("/health", response_model=HealthResponse, tags=["utility"])
def health():
    papers_conn = get_connection("papers")
    reviews_conn = get_connection("reviews")
    paper_count = papers_conn.execute(
        "SELECT COUNT(*) FROM papers WHERE is_current = 1"
    ).fetchone()[0]
    reviews_count = reviews_conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE is_current = 1"
    ).fetchone()[0]
    return {
        "status": "ok",
        "paper_count": paper_count,
        "db_last_synced": get_last_synced("papers"),
        "reviews_count": reviews_count,
        "reviews_last_synced": get_last_synced("reviews"),
    }


@app.post("/admin/refresh-db", tags=["admin"])
def admin_refresh_db(
    x_admin_key: str = Header(),
    target: str = Query("all", pattern="^(all|papers|reviews)$"),
):
    settings = get_settings()
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(403, "Invalid admin key")
    refreshed: list[str] = []
    if target in ("all", "papers"):
        refresh_db("papers", settings.gcs_db_url)
        refreshed.append("papers")
    if target in ("all", "reviews"):
        refresh_db("reviews", settings.reviews_gcs_db_url)
        refreshed.append("reviews")
    return {
        "status": "refreshed",
        "refreshed": refreshed,
        "db_last_synced": get_last_synced("papers"),
        "reviews_last_synced": get_last_synced("reviews"),
    }


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("main:app", host=s.host, port=s.port, reload=True)
