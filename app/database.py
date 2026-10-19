"""SQLite connection management with GCS download support.

Supports multiple named backends (e.g. "papers", "reviews"), each with its
own SQLite DB downloaded from GCS. All DBs are read-only from this service's
perspective — they're populated by upstream pipelines and synced to GCS.
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_lock = threading.Lock()
_conns: dict[str, sqlite3.Connection] = {}
_db_paths: dict[str, str] = {}
_last_synced: dict[str, str | None] = {}
# Serialises a whole refresh. _lock above guards only the connection swap,
# which is not enough: every file step in refresh_db() derives its paths from
# db_path, so two concurrent refreshes share them. That is not hypothetical --
# a bulk ingest upstream fires one /admin/refresh-db push per batch, and the
# periodic poll lands in the middle of them.
_refresh_lock = threading.Lock()
# Monotonic per-backend counter: every refresh gets a file of its own.
_generation: dict[str, int] = {}
# The file each live connection is actually open on, which after the first
# refresh is a generation file rather than db_path.
_live_paths: dict[str, str] = {}


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


def _sidecars(path: str) -> tuple[str, ...]:
    """A SQLite database and the two files _open() creates beside it.

    _open() sets ``PRAGMA journal_mode=WAL``, so every connection brings a
    ``-wal`` and a ``-shm`` into being next to its database. They are the
    reason this module cannot treat the database as a single file.
    """
    return (path, path + "-wal", path + "-shm")


def _discard(path: str) -> None:
    """Delete a database and its sidecars, ignoring what is not there."""
    for candidate in _sidecars(path):
        try:
            os.unlink(candidate)
        except OSError:
            pass


def _open(key: str, path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # Ensure citations table exists on the papers DB (may be missing from older DBs).
    if key == "papers":
        conn.executescript(CITATIONS_TABLE_SQL)
    conn.execute("PRAGMA query_only=ON")
    return conn


_GCS_HTTPS_PREFIXES = (
    "https://storage.googleapis.com/",
    "http://storage.googleapis.com/",
    "https://storage.cloud.google.com/",
)


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    """Split a GCS location into ``(bucket, blob_path)``.

    Accepts both ``gs://bucket/path`` and the legacy public
    ``https://storage.googleapis.com/bucket/path`` form, so a stale
    ``PX_API_GCS_DB_URL`` override doesn't break the container.
    """
    rest = uri
    for prefix in _GCS_HTTPS_PREFIXES:
        if rest.startswith(prefix):
            rest = rest[len(prefix):]
            break
    else:
        if not rest.startswith("gs://"):
            raise ValueError(f"Unsupported GCS location: {uri}")
        rest = rest[len("gs://"):]
    bucket, _, blob = rest.partition("/")
    if not bucket or not blob:
        raise ValueError(f"Unsupported GCS location: {uri}")
    return bucket, blob


def _download_from_gcs(key: str, url: str, dest: str) -> None:
    """Download a DB from GCS and log its size + row count.

    Uses the authenticated ``google-cloud-storage`` client rather than the
    public ``storage.googleapis.com`` URL. Anonymous reads of these buckets
    stopped working on 2026-07-11 when org-level Public Access Prevention was
    enforced — it overrides the buckets' surviving ``allUsers`` grant, so every
    unauthenticated GET became a 403 and this service crashed on startup for
    13 days. The authenticated API also hits the storage tier directly rather
    than Google's frontend HTTP cache, so a refresh can't land a stale
    snapshot (the bug arxiv-browse hit and documented).

    Downloads to a sibling ``.part`` file and renames on success, so a failed
    or truncated transfer can never leave a corrupt DB at ``dest``.
    """
    from google.cloud import storage

    bucket_name, blob_path = _parse_gcs_uri(url)
    log.info("Downloading %s DB from gs://%s/%s", key, bucket_name, blob_path)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    part = dest + ".part"
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_path).download_to_filename(part)
    try:
        size = os.path.getsize(part)
        count = 0
        query = _VALIDATION_QUERIES.get(key)
        if query:
            c = sqlite3.connect(part)
            try:
                count = c.execute(query).fetchone()[0]
            finally:
                c.close()
    except Exception:
        os.unlink(part)
        raise
    os.replace(part, dest)
    log.info("Downloaded %s DB: %d bytes, %d rows", key, size, count)


def init_db(key: str, db_path: str, gcs_url: str | None = None) -> None:
    """Download the named DB from GCS if configured, then open the connection.

    A download failure is logged and swallowed rather than raised. This runs
    inside the FastAPI lifespan, so raising kills the whole process — which is
    exactly how a GCS permission change took every endpoint offline, not just
    the ones that needed the DB. Instead we fall back to any previously
    downloaded file and let the periodic refresh recover.
    """
    _db_paths[key] = db_path
    _live_paths[key] = db_path
    # Generation files and part-downloads left by a previous container, which
    # are whole copies of the database and so worth reclaiming. Also the
    # ".new" path the pre-generation refresh used, whose orphaned WAL sidecars
    # are what used to make every refresh after the first fail.
    for stale in sorted(Path(db_path).parent.glob(Path(db_path).name + ".*")):
        if stale.name.endswith((".part", ".new")) or ".gen" in stale.name:
            _discard(str(stale).removesuffix("-wal").removesuffix("-shm"))
    if gcs_url:
        try:
            _download_from_gcs(key, gcs_url, db_path)
            _last_synced[key] = datetime.now(timezone.utc).isoformat()
        except Exception:
            log.exception("Failed to download %s DB from GCS", key)
            _last_synced.setdefault(key, None)
    else:
        _last_synced.setdefault(key, None)
    if not os.path.exists(db_path):
        log.error(
            "No local %s DB at %s — '%s' endpoints stay unavailable until a "
            "refresh succeeds",
            key,
            db_path,
            key,
        )
        return
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
    """Re-download the named DB from GCS and swap its connection atomically.

    Each refresh lands on a generation file of its own and the superseded one is
    deleted once its connection is closed, so no path is ever renamed over
    while a connection holds it open. That is what used to break this.

    The old sequence downloaded to ``<db>.new``, opened a connection on it --
    creating ``<db>.new-wal`` and ``<db>.new-shm`` -- and only then renamed
    ``<db>.new`` to db_path, moving the database out from under its own
    sidecars and leaving them behind. The next refresh's ``os.replace()`` onto
    ``<db>.new`` then had to overwrite a path with live WAL mappings, which on
    Cloud Run's sandboxed filesystem fails with EPERM, "Operation not
    permitted". So every refresh after a container's first failed -- the
    periodic poll and the push alike, the latter surfacing upstream as a bare
    HTTP 500 -- and the service answered from whatever the database held at
    cold start. It went unnoticed for a month because the only visible symptom
    was a paper count that moved when a container restarted and at no other
    time, and stale-but-plausible is indistinguishable from correct until the
    real number moves sharply.
    """
    db_path = _db_paths.get(key)
    if db_path is None:
        raise RuntimeError(f"Database '{key}' not initialized. Call init_db() first.")

    with _refresh_lock:
        generation = _generation.get(key, 0) + 1
        new_path = f"{db_path}.gen{generation}"
        # An attempt that died mid-download may have left this path behind; it
        # carries no open connection, so it is safe to clear.
        _discard(new_path)
        _download_from_gcs(key, gcs_url, new_path)
        try:
            new_conn = _open(key, new_path)
        except Exception:
            _discard(new_path)
            raise

        with _lock:
            old_conn = _conns.get(key)
            old_path = _live_paths.get(key)
            _conns[key] = new_conn
            _live_paths[key] = new_path
            _generation[key] = generation
            _last_synced[key] = datetime.now(timezone.utc).isoformat()

        if old_conn:
            old_conn.close()
        # Only now that nothing is reading it can the superseded generation go.
        # db_path itself is never deleted: it is the cold-start download, and
        # leaving it means a restart that cannot reach GCS still has a database
        # to fall back on.
        if old_path and old_path != db_path:
            _discard(old_path)

    log.info("%s DB refreshed successfully (generation %d)", key, generation)
