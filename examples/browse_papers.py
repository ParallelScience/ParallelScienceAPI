"""Example: browse papers, authors, categories, and stats.

Usage:
    python browse_python.py

Requires: pip install httpx
"""

import httpx

API = "https://parallel-science-api-689836870161.us-central1.run.app/api/v1"
# Uncomment the line below to use a local server instead of the remote API
#API="http://localhost:8080/api/v1"

def main():
    # ── List papers ─────────────────────────────────────────────────────
    results = httpx.get(f"{API}/papers", params={"per_page": 5}).json()
    print(f"Papers ({results['pagination']['total']} total, showing first 5):")
    for p in results["papers"]:
        print(f"  [{p['px_id']}] {p['title'][:70]}")
    print()

    # ── Search ──────────────────────────────────────────────────────────
    results = httpx.get(f"{API}/papers", params={"search": "dark matter"}).json()
    print(f"Search 'dark matter': {results['pagination']['total']} result(s)")
    for p in results["papers"]:
        print(f"  [{p['px_id']}] {p['title']}")
    print()

    # ── Filter by category ──────────────────────────────────────────────
    results = httpx.get(f"{API}/papers", params={"category": "cs.AI"}).json()
    print(f"Papers in cs.AI: {results['pagination']['total']}")
    for p in results["papers"]:
        print(f"  [{p['px_id']}] {p['title'][:70]}")
    print()

    # ── Authors ─────────────────────────────────────────────────────────
    authors = httpx.get(f"{API}/authors").json()
    print("Authors:")
    for a in authors["authors"]:
        print(f"  {a['name']} ({a['paper_count']} paper(s))")
    print()

    # ── Categories ──────────────────────────────────────────────────────
    categories = httpx.get(f"{API}/categories").json()
    print("Categories:")
    for c in categories:
        print(f"  {c['code']:20s} {c['name']:40s} ({c['paper_count']} papers)")
    print()

    # ── Statistics ──────────────────────────────────────────────────────
    stats = httpx.get(f"{API}/stats").json()
    print(f"Total papers:     {stats['total_papers']}")
    print(f"Total authors:    {stats['total_authors']}")
    print(f"Total categories: {stats['total_categories']}")
    print(f"Latest paper:     {stats['latest_paper_date']}")
    print()

    # ── Submission timeline ─────────────────────────────────────────────
    timeline = httpx.get(f"{API}/stats/submissions", params={"group_by": "month"}).json()
    print("Submissions by month:")
    for point in timeline:
        bar = "#" * point["count"]
        print(f"  {point['period']}  {bar} ({point['count']})")
    print()

    # ── Category distribution ───────────────────────────────────────────
    cat_stats = httpx.get(f"{API}/stats/categories").json()
    print("Papers per category:")
    for c in cat_stats:
        bar = "#" * c["count"]
        print(f"  {c['category']:20s} {bar} ({c['count']})")


if __name__ == "__main__":
    main()
