"""Example: browse reviews, filter, fetch scores, and review stats.

Usage:
    python browse_reviews.py

Requires: pip install httpx
"""

import httpx

API = "https://parallel-science-api-689836870161.us-central1.run.app/api/v1"
# Uncomment the line below to use a local server instead of the remote API
#API = "http://localhost:8080/api/v1"


def main():
    # ── List reviews ────────────────────────────────────────────────────
    results = httpx.get(f"{API}/reviews", params={"per_page": 5}).json()
    print(f"Reviews ({results['pagination']['total']} total, showing first 5):")
    for r in results["reviews"]:
        overall = r["scores"]["overall"]
        score = f"score={overall}" if overall is not None else "unscored"
        print(f"  [{r['review_id']}] {r['paper_title'][:60]}  ({score})")
    print()

    # ── Filter by paper PX ID ───────────────────────────────────────────
    if results["reviews"]:
        px_id = results["reviews"][0]["px_id"]
        by_paper = httpx.get(f"{API}/reviews", params={"px_id": px_id}).json()
        print(f"Reviews for paper {px_id}: {by_paper['pagination']['total']}")
        for r in by_paper["reviews"]:
            print(f"  [{r['review_id']}]  {r['review_date']}")
        print()

    # ── Filter by minimum overall score ─────────────────────────────────
    top = httpx.get(f"{API}/reviews", params={"min_score": 8}).json()
    print(f"Reviews with overall score >= 8: {top['pagination']['total']}")
    for r in top["reviews"][:5]:
        print(f"  [{r['review_id']}] overall={r['scores']['overall']}  {r['paper_title'][:50]}")
    print()

    # ── Fetch a single review's scores ──────────────────────────────────
    if results["reviews"]:
        review_id = results["reviews"][0]["review_id"]
        scores = httpx.get(f"{API}/reviews/{review_id}/scores").json()
        print(f"Scores for {review_id}:")
        for key, value in scores.items():
            if key == "justification":
                continue
            print(f"  {key:13s} {value}")
        if scores.get("justification"):
            print(f"  justification: {scores['justification'][:100]}")
        print()

    # ── Review stats ────────────────────────────────────────────────────
    stats = httpx.get(f"{API}/stats/reviews").json()
    print("Review statistics:")
    print(f"  Total reviews:         {stats['total_reviews']}")
    print(f"  Papers reviewed:       {stats['total_papers_reviewed']}")
    print(f"  Latest review date:    {stats['latest_review_date']}")
    avg = stats["average_scores"]
    print("  Average scores:")
    for k, v in avg.items():
        shown = f"{v:.2f}" if v is not None else "n/a"
        print(f"    {k:13s} {shown}")
    print()

    # ── Top rated reviews ───────────────────────────────────────────────
    ranked = httpx.get(f"{API}/stats/reviews/top-rated", params={"limit": 5}).json()
    print("Top rated reviews:")
    for r in ranked:
        print(f"  overall={r['score_overall']}  [{r['review_id']}]  {r['paper_title'][:60]}")
    print()

    # ── Reviews-per-paper histogram ─────────────────────────────────────
    hist = httpx.get(f"{API}/stats/reviews/by-paper").json()
    print("Reviews-per-paper distribution:")
    for bucket in hist:
        bar = "#" * bucket["paper_count"]
        print(f"  {bucket['reviews_per_paper']} review(s): {bar} ({bucket['paper_count']} paper(s))")


if __name__ == "__main__":
    main()
