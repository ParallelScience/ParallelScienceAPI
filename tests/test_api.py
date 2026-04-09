"""Tests for all API endpoints."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["paper_count"] == 3  # 3 current papers


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
