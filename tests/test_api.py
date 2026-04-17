"""Tests for all API endpoints."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["paper_count"] == 3  # 3 current papers
    assert data["reviews_count"] == 3  # 3 current reviews
    assert data["reviews_last_synced"] is not None


# --- Papers ---

def test_list_papers(client):
    r = client.get("/api/v1/papers")
    assert r.status_code == 200
    data = r.json()
    assert len(data["papers"]) == 3
    assert data["pagination"]["total"] == 3


def test_list_papers_category_filter(client):
    r = client.get("/api/v1/papers", params={"category": "cs.AI"})
    assert r.status_code == 200
    data = r.json()
    # 2604.00002 (current v2) has primary_category=cs.AI
    # 2604.00001 has secondary cs.AI
    assert len(data["papers"]) >= 1


def test_list_papers_search(client):
    r = client.get("/api/v1/papers", params={"search": "dark matter"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["papers"]) == 1
    assert data["papers"][0]["px_id"] == "2604.00001"


def test_list_papers_pagination(client):
    r = client.get("/api/v1/papers", params={"per_page": 1, "page": 1})
    assert r.status_code == 200
    data = r.json()
    assert len(data["papers"]) == 1
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["total_pages"] == 3


def test_get_paper(client):
    r = client.get("/api/v1/papers/2604.00001")
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Dark Matter Detection with AI"
    assert data["author"] == "Alice Smith"


def test_get_paper_not_found(client):
    r = client.get("/api/v1/papers/9999.99999")
    assert r.status_code == 404


def test_get_versions(client):
    r = client.get("/api/v1/papers/2604.00002/versions")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["version"] == 1
    assert data[1]["version"] == 2


def test_get_paper_version(client):
    r = client.get("/api/v1/papers/2604.00002/versions/1")
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Neural Network Architectures for NLP"


def test_bibtex(client):
    r = client.get("/api/v1/papers/2604.00001/bibtex")
    assert r.status_code == 200
    assert "PX:2604.00001" in r.text
    assert "Dark Matter Detection with AI" in r.text


# --- Authors ---

def test_list_authors(client):
    r = client.get("/api/v1/authors")
    assert r.status_code == 200
    data = r.json()
    assert len(data["authors"]) == 2  # Alice Smith, Bob Jones


def test_get_author_papers(client):
    r = client.get("/api/v1/authors/Alice Smith/papers")
    assert r.status_code == 200
    data = r.json()
    assert len(data["papers"]) == 2  # dark matter + climate


# --- Categories ---

def test_list_categories(client):
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2  # cs.AI, physics.astro-ph, physics.ao-ph


def test_get_category(client):
    r = client.get("/api/v1/categories/cs.AI")
    assert r.status_code == 200
    data = r.json()
    assert data["code"] == "cs.AI"
    assert len(data["papers"]) >= 1


def test_get_category_archive_prefix(client):
    r = client.get("/api/v1/categories/physics")
    assert r.status_code == 200
    data = r.json()
    # Should match physics.astro-ph and physics.ao-ph
    assert len(data["papers"]) == 2


def test_get_category_not_found(client):
    r = client.get("/api/v1/categories/nonexistent.XX")
    assert r.status_code == 404


# --- Stats ---

def test_stats_overview(client):
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_papers"] == 3
    assert data["total_authors"] == 2
    assert data["total_categories"] >= 2


def test_stats_submissions(client):
    r = client.get("/api/v1/stats/submissions")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert all("period" in p and "count" in p for p in data)


def test_stats_categories(client):
    r = client.get("/api/v1/stats/categories")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2
    assert all("category" in c and "count" in c for c in data)


def test_stats_top_cited(client):
    r = client.get("/api/v1/stats/top-cited")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    # Paper 1 and 3 are cited by other PX papers
    px_ids = [p["px_id"] for p in data]
    assert "2604.00001" in px_ids or "2604.00003" in px_ids


# --- Citations ---

def test_get_references(client):
    r = client.get("/api/v1/papers/2604.00001/references")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2  # one external, one PX
    keys = {e["citation_key"] for e in data}
    assert "Smith2020" in keys
    assert "PX:2604.00003" in keys
    # Check is_px_paper flag
    for entry in data:
        if entry["citation_key"] == "PX:2604.00003":
            assert entry["is_px_paper"] is True
            assert entry["cited_px_id"] == "2604.00003"
        else:
            assert entry["is_px_paper"] is False
            assert entry["arxiv_id"] == "2001.12345"


def test_get_references_not_found(client):
    r = client.get("/api/v1/papers/9999.99999/references")
    assert r.status_code == 404


def test_get_cited_by(client):
    r = client.get("/api/v1/papers/2604.00001/cited-by")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1  # paper 2 cites paper 1
    assert data[0]["citing_px_id"] == "2604.00002"


def test_get_cited_by_empty(client):
    r = client.get("/api/v1/papers/2604.00002/cited-by")
    assert r.status_code == 200
    assert r.json() == []  # nobody cites paper 2


def test_citation_counts(client):
    r = client.get("/api/v1/papers/2604.00001/citation-counts")
    assert r.status_code == 200
    data = r.json()
    assert data["px_id"] == "2604.00001"
    assert data["references_count"] == 2    # cites 2 papers
    assert data["px_references_count"] == 1  # 1 is a PX paper
    assert data["cited_by_count"] == 1       # cited by paper 2
    assert data["external_cited_by_count"] == 2  # 2 external arXiv papers


def test_citation_counts_not_found(client):
    r = client.get("/api/v1/papers/9999.99999/citation-counts")
    assert r.status_code == 404


def test_get_external_cited_by(client):
    """Paper 2604.00001 has two external arXiv citations; newer first."""
    r = client.get("/api/v1/papers/2604.00001/external-cited-by")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    # Ordered by posted_date DESC
    assert data[0]["external_id"] == "2504.22222"
    assert data[0]["external_version"] == "v2"
    assert data[0]["source"] == "arxiv"
    assert data[0]["match_method"] == "bib_archive_prefix"
    assert data[1]["external_id"] == "2504.11111"


def test_get_external_cited_by_single(client):
    r = client.get("/api/v1/papers/2604.00002/external-cited-by")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["external_id"] == "2504.33333"
    assert data[0]["match_method"] == "tex_regex"


def test_get_external_cited_by_empty(client):
    """A paper with no external citations returns [] (not 404)."""
    r = client.get("/api/v1/papers/2604.00003/external-cited-by")
    assert r.status_code == 200
    assert r.json() == []


def test_get_external_cited_by_unknown_paper(client):
    """Unknown PX ID also returns [], consistent with /cited-by."""
    r = client.get("/api/v1/papers/9999.99999/external-cited-by")
    assert r.status_code == 200
    assert r.json() == []
