"""Parallel ArXiv API — FastAPI entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException

from app.config import get_settings
from app.database import get_connection, get_last_synced, init_db, refresh_db
from app.models import HealthResponse
from app.routers import authors, categories, citations, papers, stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger(__name__)


async def _periodic_refresh(settings) -> None:
    """Background task to refresh the DB from GCS periodically."""
    interval = settings.db_refresh_interval_minutes * 60
    while True:
        await asyncio.sleep(interval)
        try:
            log.info("Periodic DB refresh starting")
            refresh_db(settings.gcs_db_url)
        except Exception:
            log.exception("Periodic DB refresh failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings.db_path, settings.gcs_db_url)
    task = asyncio.create_task(_periodic_refresh(settings))
    yield
    task.cancel()


app = FastAPI(
    title="Parallel ArXiv API",
    description="REST API for querying AI-generated research papers on Parallel ArXiv (papers.parallelscience.org).",
    version="0.1.0",
    lifespan=lifespan,
)

prefix = get_settings().api_v1_prefix
app.include_router(papers.router, prefix=prefix)
app.include_router(authors.router, prefix=prefix)
app.include_router(categories.router, prefix=prefix)
app.include_router(citations.router, prefix=prefix)
app.include_router(stats.router, prefix=prefix)


@app.get("/health", response_model=HealthResponse, tags=["utility"])
def health():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM papers WHERE is_current = 1").fetchone()[0]
    return {"status": "ok", "paper_count": count, "db_last_synced": get_last_synced()}


@app.post("/admin/refresh-db", tags=["admin"])
def admin_refresh_db(x_admin_key: str = Header()):
    settings = get_settings()
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(403, "Invalid admin key")
    refresh_db(settings.gcs_db_url)
    return {"status": "refreshed", "db_last_synced": get_last_synced()}


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("main:app", host=s.host, port=s.port, reload=True)
