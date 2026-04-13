"""SQLite connection management with GCS download support.

Supports multiple named backends (e.g. "papers", "reviews"), each with its
own SQLite DB downloaded from GCS. All DBs are read-only from this service's
perspective — they're populated by upstream pipelines and synced to GCS.
"""

import logging
import os
import sqlite3
import threading
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_lock = threading.Lock()
_conns: dict[str, sqlite3.Connection] = {}
_db_paths: dict[str, str] = {}
_last_synced: dict[str, str | None] = {}


CITATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS citations (
    citing_px_id TEXT NOT NULL, citation_key TEXT NOT NULL,
    cited_px_id TEXT, arxiv_id TEXT, doi TEXT, title TEXT, authors TEXT, year TEXT,
    created_at TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (citing_px_id, citation_key));
CREATE INDEX IF NOT EXISTS idx_citations_cited_px ON citations(cited_px_id) WHERE cited_px_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_px_id);
"""


# Per-backend sanity-check queries for the GCS download validation step.
_VALIDATION_QUERIES: dict[str, str] = {
    "papers": "SELECT count(*) FROM papers",
    "reviews": "SELECT count(*) FROM reviews",
}


def _open(key: str, path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # Ensure citations table exists on the papers DB (may be missing from older DBs).
    if key == "papers":
        conn.executescript(CITATIONS_TABLE_SQL)
    conn.execute("PRAGMA query_only=ON")
    return conn


def _download_from_gcs(key: str, url: str, dest: str) -> None:
    """Download a DB from a GCS public URL and log its size + row count."""
    log.info("Downloading %s DB from %s", key, url)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    size = os.path.getsize(dest)
    count = 0
    query = _VALIDATION_QUERIES.get(key)
    if query:
        c = sqlite3.connect(dest)
        try:
            count = c.execute(query).fetchone()[0]
        finally:
            c.close()
    log.info("Downloaded %s DB: %d bytes, %d rows", key, size, count)


def init_db(key: str, db_path: str, gcs_url: str | None = None) -> None:
    """Download the named DB from GCS if configured, then open the connection."""
    _db_paths[key] = db_path
    if gcs_url:
        _download_from_gcs(key, gcs_url, db_path)
        _last_synced[key] = datetime.now(timezone.utc).isoformat()
    else:
        _last_synced.setdefault(key, None)
    _conns[key] = _open(key, db_path)


def get_connection(key: str) -> sqlite3.Connection:
    """Return the shared read-only connection for the named backend."""
    conn = _conns.get(key)
    if conn is None:
        raise RuntimeError(f"Database '{key}' not initialized. Call init_db() first.")
    return conn


def get_last_synced(key: str) -> str | None:
    return _last_synced.get(key)


def refresh_db(key: str, gcs_url: str) -> None:
    """Re-download the named DB from GCS and swap its connection atomically."""
    db_path = _db_paths.get(key)
    if db_path is None:
        raise RuntimeError(f"Database '{key}' not initialized. Call init_db() first.")
    tmp_path = db_path + ".new"
    _download_from_gcs(key, gcs_url, tmp_path)
    new_conn = _open(key, tmp_path)
    with _lock:
        old = _conns.get(key)
        _conns[key] = new_conn
        _last_synced[key] = datetime.now(timezone.utc).isoformat()
    if old:
        old.close()
    os.replace(tmp_path, db_path)
    log.info("%s DB refreshed successfully", key)
