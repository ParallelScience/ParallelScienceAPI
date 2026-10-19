"""refresh_db() must be able to run more than once.

The bug these cover was not a crash but a silence: refresh_db() opened a
connection on ``<db>.new`` -- which, because _open() sets journal_mode=WAL,
created ``<db>.new-wal`` and ``<db>.new-shm`` -- then renamed ``<db>.new`` onto
db_path, orphaning those sidecars. The NEXT refresh had to os.replace() onto
``<db>.new`` while those mappings were live, which Cloud Run's filesystem
refuses with EPERM. Every refresh after a container's first failed for a month;
the only symptom was a stats count that moved on restart and never otherwise.

A plain Linux filesystem permits that rename, so asserting "the second refresh
raises" would not reproduce it here. These assert the invariant instead: a
refresh leaves no database file behind with sidecars beside it, and the
connection really does serve the new content.
"""

import sqlite3
import threading

import pytest

from app import database
# Bound at import time, which is collection time -- before any fixture runs.
# conftest's session-scoped `client` fixture replaces database.init_db with a
# no-op lambda for the whole session (so the FastAPI lifespan cannot overwrite
# its in-memory DBs) and only restores it at session teardown, so reaching for
# database.init_db here would get the stub whenever the full suite runs.
from app.database import init_db as real_init_db


def _write_db(path, rows):
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS papers ("
        "  px_id TEXT PRIMARY KEY, is_current INTEGER NOT NULL DEFAULT 1);"
    )
    conn.executemany(
        "INSERT OR REPLACE INTO papers (px_id) VALUES (?)",
        [(f"PX:2610.{i:05d}",) for i in range(rows)],
    )
    conn.commit()
    conn.close()


@pytest.fixture
def fake_gcs(tmp_path, monkeypatch):
    """Stand in for the GCS download with a local copy, and isolate module state."""
    source = tmp_path / "remote.db"
    state = {"rows": 2}

    def fake_download(key, url, dest):
        _write_db(source, state["rows"])
        # Mirrors the real _download_from_gcs: land on a .part, then rename.
        part = dest + ".part"
        part_path = tmp_path / part.rsplit("/", 1)[-1]
        part_path.write_bytes(source.read_bytes())
        import os
        os.replace(part_path, dest)

    monkeypatch.setattr(database, "_download_from_gcs", fake_download)
    for attr in ("_conns", "_db_paths", "_last_synced", "_generation", "_live_paths"):
        # raising=False so these tests can also be run against the unfixed
        # module, which has neither _generation nor _live_paths.
        monkeypatch.setattr(database, attr, {}, raising=False)

    db_path = str(tmp_path / "papers.db")
    _write_db(db_path, state["rows"])
    real_init_db("papers", db_path, gcs_url=None)
    yield state, db_path, tmp_path
    conn = database._conns.get("papers")
    if conn:
        conn.close()


def _count(key="papers"):
    return database.get_connection(key).execute(
        "SELECT count(*) FROM papers"
    ).fetchone()[0]


def _orphans(tmp_path, db_path):
    """Database files beside db_path that still have WAL/SHM sidecars."""
    live = database._live_paths.get("papers")
    out = []
    for sidecar in tmp_path.glob("papers.db*-wal"):
        owner = str(sidecar)[: -len("-wal")]
        if owner not in (live, db_path):
            out.append(owner)
    return out


def test_refresh_twice_succeeds(fake_gcs):
    """The second refresh is the one that used to fail."""
    state, db_path, tmp_path = fake_gcs
    assert _count() == 2

    state["rows"] = 5
    database.refresh_db("papers", "gs://bucket/papers.db")
    assert _count() == 5

    state["rows"] = 9
    database.refresh_db("papers", "gs://bucket/papers.db")
    assert _count() == 9, "the refresh ran but the connection still serves stale rows"


def test_refresh_leaves_no_orphaned_sidecars(fake_gcs):
    """No superseded database may keep a WAL mapping -- that is the EPERM."""
    state, db_path, tmp_path = fake_gcs
    for rows in (3, 4, 5, 6):
        state["rows"] = rows
        database.refresh_db("papers", "gs://bucket/papers.db")
        assert _count() == rows
        assert not _orphans(tmp_path, db_path), (
            f"after {rows} rows, orphaned: {_orphans(tmp_path, db_path)}"
        )


def test_cold_start_file_is_kept(fake_gcs):
    """db_path survives, so a restart that cannot reach GCS still has data."""
    state, db_path, tmp_path = fake_gcs
    state["rows"] = 7
    database.refresh_db("papers", "gs://bucket/papers.db")
    import os
    assert os.path.exists(db_path)


def test_generations_do_not_accumulate(fake_gcs):
    """Each refresh reclaims the last one; these files are whole DB copies."""
    state, db_path, tmp_path = fake_gcs
    for rows in range(2, 8):
        state["rows"] = rows
        database.refresh_db("papers", "gs://bucket/papers.db")
    gens = sorted(p.name for p in tmp_path.glob("papers.db.gen*")
                  if not p.name.endswith(("-wal", "-shm")))
    assert len(gens) == 1, f"generation files piled up: {gens}"


def test_concurrent_refreshes_are_serialised(fake_gcs):
    """The poll and a push arrive together whenever a bulk ingest fires."""
    state, db_path, tmp_path = fake_gcs
    state["rows"] = 4
    errors = []

    def go():
        try:
            for _ in range(3):
                database.refresh_db("papers", "gs://bucket/papers.db")
        except Exception as exc:  # noqa: BLE001 - the assertion is "none at all"
            errors.append(exc)

    threads = [threading.Thread(target=go) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent refreshes raised: {errors}"
    assert _count() == 4
    assert not _orphans(tmp_path, db_path)
