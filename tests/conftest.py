"""Test fixtures: in-memory SQLite DB + FastAPI TestClient."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS id_registry (
    repo        TEXT PRIMARY KEY,
    px_id       TEXT NOT NULL UNIQUE,
    yymm        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS id_sequence (
    yymm    TEXT PRIMARY KEY,
    next_n  INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS papers (
    px_id               TEXT NOT NULL,
    version             INTEGER NOT NULL DEFAULT 1,
    title               TEXT NOT NULL,
    author              TEXT NOT NULL,
    date                TEXT NOT NULL,
    abstract            TEXT NOT NULL,
    primary_category    TEXT NOT NULL,
    secondary_categories TEXT NOT NULL DEFAULT '[]',
    repo                TEXT NOT NULL,
    pages_url           TEXT NOT NULL,
    github_url          TEXT NOT NULL,
    pdf_url             TEXT NOT NULL,
    is_current          INTEGER NOT NULL DEFAULT 1,
    scraped_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    content_hash        TEXT,
    PRIMARY KEY (px_id, version)
);
CREATE INDEX IF NOT EXISTS idx_papers_current ON papers(is_current) WHERE is_current = 1;
CREATE INDEX IF NOT EXISTS idx_papers_category ON papers(primary_category) WHERE is_current = 1;
CREATE INDEX IF NOT EXISTS idx_papers_author ON papers(author) WHERE is_current = 1;
CREATE INDEX IF NOT EXISTS idx_papers_repo ON papers(repo);

CREATE TABLE IF NOT EXISTS citations (
    citing_px_id TEXT NOT NULL, citation_key TEXT NOT NULL,
    cited_px_id TEXT, arxiv_id TEXT, doi TEXT, title TEXT, authors TEXT, year TEXT,
    created_at TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (citing_px_id, citation_key));
CREATE INDEX IF NOT EXISTS idx_citations_cited_px ON citations(cited_px_id) WHERE cited_px_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_px_id);
"""

SEED_DATA = [
    {
        "px_id": "2604.00001", "version": 1, "title": "Dark Matter Detection with AI",
        "author": "Alice Smith", "date": "2026-04-01 10:00:00",
        "abstract": "We present a novel approach to dark matter detection using machine learning.",
        "primary_category": "physics.astro-ph", "secondary_categories": '["cs.AI"]',
        "repo": "dark-matter-ai", "pages_url": "https://example.com/dark-matter-ai",
        "github_url": "https://github.com/ParallelScience/dark-matter-ai",
        "pdf_url": "https://storage.googleapis.com/parallel-arxiv-pdfs/2604.00001v1.pdf",
        "is_current": 1, "content_hash": "abc123",
    },
    {
        "px_id": "2604.00002", "version": 1, "title": "Neural Network Architectures for NLP",
        "author": "Bob Jones", "date": "2026-04-02 12:00:00",
        "abstract": "A comprehensive study of transformer architectures for natural language processing.",
        "primary_category": "cs.AI", "secondary_categories": '["cs.CL"]',
        "repo": "nlp-transformers", "pages_url": "https://example.com/nlp-transformers",
        "github_url": "https://github.com/ParallelScience/nlp-transformers",
        "pdf_url": "https://storage.googleapis.com/parallel-arxiv-pdfs/2604.00002v1.pdf",
        "is_current": 1, "content_hash": "def456",
    },
    {
        "px_id": "2604.00002", "version": 2, "title": "Neural Network Architectures for NLP (v2)",
        "author": "Bob Jones", "date": "2026-04-05 14:00:00",
        "abstract": "Updated study of transformer architectures for natural language processing.",
        "primary_category": "cs.AI", "secondary_categories": '["cs.CL"]',
        "repo": "nlp-transformers", "pages_url": "https://example.com/nlp-transformers",
        "github_url": "https://github.com/ParallelScience/nlp-transformers",
        "pdf_url": "https://storage.googleapis.com/parallel-arxiv-pdfs/2604.00002v2.pdf",
        "is_current": 1, "content_hash": "ghi789",
    },
    {
        "px_id": "2604.00003", "version": 1, "title": "Climate Modeling with Deep Learning",
        "author": "Alice Smith", "date": "2026-04-03 09:00:00",
        "abstract": "Deep learning methods applied to climate prediction and modeling.",
        "primary_category": "physics.ao-ph", "secondary_categories": '["cs.LG"]',
        "repo": "climate-dl", "pages_url": "https://example.com/climate-dl",
        "github_url": "https://github.com/ParallelScience/climate-dl",
        "pdf_url": "https://storage.googleapis.com/parallel-arxiv-pdfs/2604.00003v1.pdf",
        "is_current": 1, "content_hash": "jkl012",
    },
]


@pytest.fixture(scope="session")
def test_db():
    """Create an in-memory SQLite DB with test data."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)

    # Mark old version of paper 2 as not current
    for paper in SEED_DATA:
        cols = ", ".join(paper.keys())
        placeholders = ", ".join(["?"] * len(paper))
        conn.execute(f"INSERT INTO papers ({cols}) VALUES ({placeholders})", list(paper.values()))

    # Mark v1 of 2604.00002 as not current
    conn.execute(
        "UPDATE papers SET is_current = 0 WHERE px_id = '2604.00002' AND version = 1"
    )

    # Seed citation data
    citations = [
        # Paper 1 cites an external arXiv paper and paper 3
        ("2604.00001", "Smith2020", None, "2001.12345", None, "External Paper", "Smith J.", "2020"),
        ("2604.00001", "PX:2604.00003", "2604.00003", None, None, "Climate Modeling with Deep Learning", "Alice Smith", "2026"),
        # Paper 2 (current v2) cites paper 1
        ("2604.00002", "PX:2604.00001", "2604.00001", None, None, "Dark Matter Detection with AI", "Alice Smith", "2026"),
        ("2604.00002", "Jones2019", None, "1912.54321", None, "Another External", "Jones B.", "2019"),
        # Paper 3 cites an external paper
        ("2604.00003", "Lee2021", None, "2103.99999", None, "Deep Learning Review", "Lee K.", "2021"),
    ]
    for c in citations:
        conn.execute(
            "INSERT INTO citations (citing_px_id, citation_key, cited_px_id, arxiv_id, doi, title, authors, year) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", c
        )

    conn.commit()
    return conn


@pytest.fixture(scope="session")
def client(test_db):
    """FastAPI TestClient with the test DB injected."""
    import app.database as db_mod

    # Patch init_db to be a no-op so the lifespan doesn't overwrite our test DB
    original_init = db_mod.init_db
    db_mod.init_db = lambda *a, **kw: None
    db_mod._conn = test_db
    db_mod._last_synced = "2026-04-09T00:00:00+00:00"

    from main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    db_mod.init_db = original_init
