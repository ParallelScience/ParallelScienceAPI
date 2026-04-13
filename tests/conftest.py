"""Test fixtures: in-memory SQLite DBs (papers + reviews) + FastAPI TestClient."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

PAPERS_SCHEMA_SQL = """
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

REVIEWS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS id_registry (
    repo         TEXT PRIMARY KEY,
    review_id    TEXT NOT NULL UNIQUE,
    px_id        TEXT NOT NULL DEFAULT '',
    paper_repo   TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS reviews (
    review_id           TEXT NOT NULL,
    version             INTEGER NOT NULL DEFAULT 1,
    paper_title         TEXT NOT NULL,
    paper_author        TEXT NOT NULL,
    review_date         TEXT NOT NULL,
    summary             TEXT NOT NULL DEFAULT '',
    strengths           TEXT NOT NULL DEFAULT '',
    major_issues        TEXT NOT NULL DEFAULT '',
    minor_issues        TEXT NOT NULL DEFAULT '',
    very_minor_issues   TEXT NOT NULL DEFAULT '',
    maths_audit         TEXT NOT NULL DEFAULT '',
    numerics_audit      TEXT NOT NULL DEFAULT '',
    reviewer            TEXT NOT NULL DEFAULT 'Skepthical',
    repo                TEXT NOT NULL,
    pages_url           TEXT NOT NULL,
    github_url          TEXT NOT NULL,
    review_pdf_url      TEXT NOT NULL DEFAULT '',
    paper_pdf_url       TEXT NOT NULL DEFAULT '',
    paper_pages_url     TEXT NOT NULL DEFAULT '',
    px_id               TEXT NOT NULL DEFAULT '',
    is_current          INTEGER NOT NULL DEFAULT 1,
    total_cost          REAL,
    score_overall       INTEGER,
    score_soundness     INTEGER,
    score_novelty       INTEGER,
    score_significance  INTEGER,
    score_clarity       INTEGER,
    score_evidence      INTEGER,
    score_justification TEXT NOT NULL DEFAULT '',
    scraped_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    content_hash        TEXT,
    PRIMARY KEY (review_id, version)
);
CREATE INDEX IF NOT EXISTS idx_reviews_current ON reviews(is_current) WHERE is_current = 1;
CREATE INDEX IF NOT EXISTS idx_reviews_author ON reviews(paper_author) WHERE is_current = 1;
CREATE INDEX IF NOT EXISTS idx_reviews_px_id ON reviews(px_id) WHERE is_current = 1;
"""

PAPERS_SEED = [
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


# Three review rows: scored / unscored / multi-version.
# Paper 2604.00001 has two reviews (R1 scored, R2 unscored).
# Paper 2604.00003 has one scored review with two versions.
REVIEWS_SEED = [
    {
        "review_id": "2604.00001-R1", "version": 1,
        "paper_title": "Dark Matter Detection with AI", "paper_author": "Alice Smith",
        "review_date": "2026-04-08 09:39:36",
        "summary": "Paper proposes ML-based DM detection.",
        "strengths": "1. Novel method\n2. Clear presentation",
        "major_issues": "1. Missing baseline comparison",
        "minor_issues": "1. Typo in eq. 3", "very_minor_issues": "",
        "maths_audit": "Consistent.", "numerics_audit": "Reproducible.",
        "reviewer": "Skepthical", "repo": "review-dark-matter-ai",
        "pages_url": "https://parallelscience.github.io/review-dark-matter-ai/",
        "github_url": "https://github.com/ParallelScience/review-dark-matter-ai",
        "review_pdf_url": "", "paper_pdf_url": "",
        "paper_pages_url": "https://example.com/dark-matter-ai",
        "px_id": "2604.00001", "is_current": 1, "total_cost": 12.34,
        "score_overall": 7, "score_soundness": 6, "score_novelty": 8,
        "score_significance": 7, "score_clarity": 6, "score_evidence": 7,
        "score_justification": "Solid work, limited baseline coverage.",
        "content_hash": "rhash1",
    },
    {
        "review_id": "2604.00001-R2", "version": 1,
        "paper_title": "Dark Matter Detection with AI", "paper_author": "Alice Smith",
        "review_date": "2026-04-09 14:15:00",
        "summary": "Secondary review of the DM paper.",
        "strengths": "1. Thorough methodology", "major_issues": "",
        "minor_issues": "1. Table formatting", "very_minor_issues": "",
        "maths_audit": "", "numerics_audit": "",
        "reviewer": "Skepthical", "repo": "review-dark-matter-ai-v2",
        "pages_url": "https://parallelscience.github.io/review-dark-matter-ai-v2/",
        "github_url": "https://github.com/ParallelScience/review-dark-matter-ai-v2",
        "review_pdf_url": "", "paper_pdf_url": "",
        "paper_pages_url": "https://example.com/dark-matter-ai",
        "px_id": "2604.00001", "is_current": 1, "total_cost": None,
        "score_overall": None, "score_soundness": None, "score_novelty": None,
        "score_significance": None, "score_clarity": None, "score_evidence": None,
        "score_justification": "",
        "content_hash": "rhash2",
    },
    {
        "review_id": "2604.00003-R1", "version": 1,
        "paper_title": "Climate Modeling with Deep Learning", "paper_author": "Alice Smith",
        "review_date": "2026-04-07 11:00:00",
        "summary": "Old version.", "strengths": "", "major_issues": "",
        "minor_issues": "", "very_minor_issues": "",
        "maths_audit": "", "numerics_audit": "",
        "reviewer": "Skepthical", "repo": "review-climate-dl",
        "pages_url": "https://parallelscience.github.io/review-climate-dl/",
        "github_url": "https://github.com/ParallelScience/review-climate-dl",
        "review_pdf_url": "", "paper_pdf_url": "",
        "paper_pages_url": "https://example.com/climate-dl",
        "px_id": "2604.00003", "is_current": 0, "total_cost": 5.00,
        "score_overall": 6, "score_soundness": 6, "score_novelty": 5,
        "score_significance": 6, "score_clarity": 7, "score_evidence": 6,
        "score_justification": "Initial review.", "content_hash": "rhash3a",
    },
    {
        "review_id": "2604.00003-R1", "version": 2,
        "paper_title": "Climate Modeling with Deep Learning", "paper_author": "Alice Smith",
        "review_date": "2026-04-10 08:00:00",
        "summary": "Updated climate review.", "strengths": "1. Strong results",
        "major_issues": "", "minor_issues": "", "very_minor_issues": "",
        "maths_audit": "Consistent.", "numerics_audit": "Numerically stable.",
        "reviewer": "Skepthical", "repo": "review-climate-dl",
        "pages_url": "https://parallelscience.github.io/review-climate-dl/",
        "github_url": "https://github.com/ParallelScience/review-climate-dl",
        "review_pdf_url": "", "paper_pdf_url": "",
        "paper_pages_url": "https://example.com/climate-dl",
        "px_id": "2604.00003", "is_current": 1, "total_cost": 6.50,
        "score_overall": 9, "score_soundness": 9, "score_novelty": 8,
        "score_significance": 9, "score_clarity": 8, "score_evidence": 9,
        "score_justification": "Revised — excellent.", "content_hash": "rhash3b",
    },
]


def _insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    for r in rows:
        cols = ", ".join(r.keys())
        placeholders = ", ".join(["?"] * len(r))
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(r.values()))


@pytest.fixture(scope="session")
def test_db():
    """In-memory papers DB with seed data."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(PAPERS_SCHEMA_SQL)

    _insert_rows(conn, "papers", PAPERS_SEED)

    # Mark v1 of 2604.00002 as not current
    conn.execute(
        "UPDATE papers SET is_current = 0 WHERE px_id = '2604.00002' AND version = 1"
    )

    citations = [
        ("2604.00001", "Smith2020", None, "2001.12345", None, "External Paper", "Smith J.", "2020"),
        ("2604.00001", "PX:2604.00003", "2604.00003", None, None, "Climate Modeling with Deep Learning", "Alice Smith", "2026"),
        ("2604.00002", "PX:2604.00001", "2604.00001", None, None, "Dark Matter Detection with AI", "Alice Smith", "2026"),
        ("2604.00002", "Jones2019", None, "1912.54321", None, "Another External", "Jones B.", "2019"),
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
def reviews_db():
    """In-memory reviews DB with seed data."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(REVIEWS_SCHEMA_SQL)
    _insert_rows(conn, "reviews", REVIEWS_SEED)
    conn.commit()
    return conn


@pytest.fixture(scope="session")
def client(test_db, reviews_db):
    """FastAPI TestClient with both DBs injected."""
    import app.database as db_mod

    # Neutralize init_db so the lifespan doesn't overwrite our in-memory DBs.
    original_init = db_mod.init_db
    db_mod.init_db = lambda *a, **kw: None
    db_mod._conns["papers"] = test_db
    db_mod._conns["reviews"] = reviews_db
    db_mod._last_synced["papers"] = "2026-04-09T00:00:00+00:00"
    db_mod._last_synced["reviews"] = "2026-04-10T00:00:00+00:00"

    from main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    db_mod.init_db = original_init
