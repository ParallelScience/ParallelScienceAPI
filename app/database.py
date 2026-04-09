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


def _open(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA journal_mode=WAL")
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
