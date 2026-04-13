"""Tests for review endpoints and cross-links."""


# --- Reviews list / filter ---

def test_list_reviews(client):
    r = client.get("/api/v1/reviews")
    assert r.status_code == 200
    data = r.json()
    # 3 current reviews seeded (R1 of paper1 scored, R2 of paper1 unscored,
    # paper3-R1 v2 scored; paper3-R1 v1 is is_current=0)
    assert data["pagination"]["total"] == 3
    ids = [r["review_id"] for r in data["reviews"]]
    assert "2604.00001-R1" in ids
    assert "2604.00001-R2" in ids
    assert "2604.00003-R1" in ids


def test_list_reviews_filter_by_px_id(client):
    r = client.get("/api/v1/reviews", params={"px_id": "2604.00001"})
    assert r.status_code == 200
    data = r.json()
    assert data["pagination"]["total"] == 2
    assert all(rev["px_id"] == "2604.00001" for rev in data["reviews"])


def test_list_reviews_filter_by_author(client):
    r = client.get("/api/v1/reviews", params={"author": "alice smith"})
    assert r.status_code == 200
    data = r.json()
    # Alice authored both paper1 and paper3 — all 3 reviews match
    assert data["pagination"]["total"] == 3


def test_list_reviews_search(client):
    r = client.get("/api/v1/reviews", params={"search": "Climate"})
    assert r.status_code == 200
    data = r.json()
    assert data["pagination"]["total"] == 1
    assert data["reviews"][0]["review_id"] == "2604.00003-R1"


def test_list_reviews_min_score(client):
    r = client.get("/api/v1/reviews", params={"min_score": 8})
    assert r.status_code == 200
    data = r.json()
    # Only paper3-R1 v2 has overall >= 8 (score 9)
    assert data["pagination"]["total"] == 1
    assert data["reviews"][0]["scores"]["overall"] == 9


def test_list_reviews_order_by_date_desc(client):
    r = client.get("/api/v1/reviews")
    assert r.status_code == 200
    dates = [rev["review_date"] for rev in r.json()["reviews"]]
    assert dates == sorted(dates, reverse=True)


# --- Review detail ---

def test_get_review(client):
    r = client.get("/api/v1/reviews/2604.00001-R1")
    assert r.status_code == 200
    data = r.json()
    assert data["review_id"] == "2604.00001-R1"
    assert data["px_id"] == "2604.00001"
    assert data["scores"]["overall"] == 7
    assert data["scores"]["justification"] == "Solid work, limited baseline coverage."
    assert data["total_cost"] == 12.34
    assert data["summary"].startswith("Paper proposes")


def test_get_review_returns_current_version(client):
    # paper3-R1 has v1 and v2; v2 is current.
    r = client.get("/api/v1/reviews/2604.00003-R1")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == 2
    assert data["scores"]["overall"] == 9
    assert data["is_current"] == 1


def test_get_review_unscored(client):
    r = client.get("/api/v1/reviews/2604.00001-R2")
    assert r.status_code == 200
    data = r.json()
    assert data["scores"]["overall"] is None
    assert data["scores"]["justification"] == ""
    assert data["total_cost"] is None


def test_get_review_not_found(client):
    r = client.get("/api/v1/reviews/9999.99999-R9")
    assert r.status_code == 404


# --- Review versions ---

def test_get_review_versions(client):
    r = client.get("/api/v1/reviews/2604.00003-R1/versions")
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[0]["is_current"] == 0
    assert versions[1]["version"] == 2
    assert versions[1]["is_current"] == 1


def test_get_review_specific_version(client):
    r = client.get("/api/v1/reviews/2604.00003-R1/versions/1")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == 1
    assert data["scores"]["overall"] == 6
    assert data["summary"] == "Old version."


def test_get_review_version_not_found(client):
    r = client.get("/api/v1/reviews/2604.00003-R1/versions/99")
    assert r.status_code == 404


def test_get_review_versions_not_found(client):
    r = client.get("/api/v1/reviews/9999.99999-R9/versions")
    assert r.status_code == 404


# --- Review scores ---

def test_get_review_scores(client):
    r = client.get("/api/v1/reviews/2604.00001-R1/scores")
    assert r.status_code == 200
    data = r.json()
    assert data["overall"] == 7
    assert data["soundness"] == 6
    assert data["novelty"] == 8
    assert data["significance"] == 7
    assert data["clarity"] == 6
    assert data["evidence"] == 7
    assert data["justification"].startswith("Solid")


def test_get_review_scores_null_when_unscored(client):
    r = client.get("/api/v1/reviews/2604.00001-R2/scores")
    assert r.status_code == 200
    data = r.json()
    assert data["overall"] is None
    assert data["justification"] == ""


def test_get_review_scores_not_found(client):
    r = client.get("/api/v1/reviews/9999.99999-R9/scores")
    assert r.status_code == 404


# --- Cross-link: /papers/{px_id}/reviews ---

def test_paper_reviews(client):
    r = client.get("/api/v1/papers/2604.00001/reviews")
    assert r.status_code == 200
    reviews = r.json()
    assert len(reviews) == 2
    assert {rev["review_id"] for rev in reviews} == {"2604.00001-R1", "2604.00001-R2"}


def test_paper_reviews_empty(client):
    # paper 2604.00002 has no reviews
    r = client.get("/api/v1/papers/2604.00002/reviews")
    assert r.status_code == 200
    assert r.json() == []


def test_paper_reviews_paper_not_found(client):
    r = client.get("/api/v1/papers/9999.99999/reviews")
    assert r.status_code == 404


# --- Review stats ---

def test_stats_reviews(client):
    r = client.get("/api/v1/stats/reviews")
    assert r.status_code == 200
    data = r.json()
    assert data["total_reviews"] == 3
    # reviews cover paper1 (2 reviews) and paper3 (1 current review)
    assert data["total_papers_reviewed"] == 2
    # Only 2 of the 3 current reviews have scores: overall 7 and 9 → avg 8.0
    assert data["average_scores"]["overall"] == 8.0
    assert data["latest_review_date"] is not None


def test_stats_reviews_top_rated(client):
    r = client.get("/api/v1/stats/reviews/top-rated")
    assert r.status_code == 200
    ranked = r.json()
    assert [x["score_overall"] for x in ranked] == sorted(
        [x["score_overall"] for x in ranked], reverse=True
    )
    assert ranked[0]["review_id"] == "2604.00003-R1"
    assert ranked[0]["score_overall"] == 9


def test_stats_reviews_by_paper(client):
    r = client.get("/api/v1/stats/reviews/by-paper")
    assert r.status_code == 200
    buckets = r.json()
    # paper1 has 2 reviews, paper3 has 1 review → {1: 1 paper, 2: 1 paper}
    d = {b["reviews_per_paper"]: b["paper_count"] for b in buckets}
    assert d == {1: 1, 2: 1}
