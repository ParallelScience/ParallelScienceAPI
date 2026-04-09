"""SQLite connection management with GCS download support.

The database is read-only from this service's perspective. It's populated
by the arxiv-browse webhook pipeline and synced to GCS.
"""

import logging
import os
import sqlite3
import threading
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_db_path: str = ""
_last_synced: str | None = None


CITATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS citations (
    citing_px_id TEXT NOT NULL, citation_key TEXT NOT NULL,
    cited_px_id TEXT, arxiv_id TEXT, doi TEXT, title TEXT, authors TEXT, year TEXT,
    created_at TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (citing_px_id, citation_key));
CREATE INDEX IF NOT EXISTS idx_citations_cited_px ON citations(cited_px_id) WHERE cited_px_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_px_id);
"""


def _open(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # Ensure citations table exists (may be missing from older DBs)
    conn.executescript(CITATIONS_TABLE_SQL)
    conn.execute("PRAGMA query_only=ON")
    return conn


def _download_from_gcs(url: str, dest: str) -> None:
    """Download the DB from GCS public URL."""
    log.info("Downloading DB from %s", url)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    size = os.path.getsize(dest)
    c = sqlite3.connect(dest)
    count = c.execute("SELECT count(*) FROM papers").fetchone()[0]
    c.close()
    log.info("Downloaded DB: %d bytes, %d papers", size, count)


def init_db(db_path: str, gcs_url: str | None = None) -> None:
    """Download DB from GCS if configured, then open the connection."""
    global _conn, _db_path, _last_synced
    _db_path = db_path
    if gcs_url:
        _download_from_gcs(gcs_url, db_path)
        _last_synced = datetime.now(timezone.utc).isoformat()
    _conn = _open(db_path)


def get_connection() -> sqlite3.Connection:
    """Return the shared read-only connection."""
    if _conn is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _conn


def get_last_synced() -> str | None:
    return _last_synced


def refresh_db(gcs_url: str) -> None:
    """Re-download DB from GCS and swap the connection atomically."""
    global _conn, _last_synced
    tmp_path = _db_path + ".new"
    _download_from_gcs(gcs_url, tmp_path)
    new_conn = _open(tmp_path)
    with _lock:
        old = _conn
        _conn = new_conn
        _last_synced = datetime.now(timezone.utc).isoformat()
    if old:
        old.close()
    os.replace(tmp_path, _db_path)
    log.info("DB refreshed successfully")
