"""Example: fetch a paper together with all of its reviews.

Usage:
    python paper_with_reviews.py [PX_ID]

Requires: pip install httpx
"""

import sys

import httpx

API = "https://orion.taila855ba.ts.net:8444/api/v1"
# Uncomment the line below to use a local server instead of the remote API
#API = "http://localhost:8080/api/v1"


def main():
    px_id = sys.argv[1] if len(sys.argv) > 1 else "2604.00003"

    paper_resp = httpx.get(f"{API}/papers/{px_id}")
    if paper_resp.status_code == 404:
        print(f"Paper {px_id} not found")
        return
    paper = paper_resp.json()
    print(f"Paper: {paper['title']}")
    print(f"  Author:   {paper['author']}")
    print(f"  Date:     {paper['date']}")
    print(f"  Category: {paper['primary_category']}")
    print()

    reviews = httpx.get(f"{API}/papers/{px_id}/reviews").json()
    if not reviews:
        print("No reviews yet.")
        return

    print(f"Reviews ({len(reviews)}):")
    for r in reviews:
        overall = r["scores"]["overall"]
        score = f"overall={overall}" if overall is not None else "unscored"
        print(f"  [{r['review_id']}]  {r['review_date']}  {score}")
        if r["scores"]["justification"]:
            print(f"    {r['scores']['justification'][:120]}")

    # Show full detail of the first review
    first = reviews[0]["review_id"]
    print()
    print(f"Full detail of {first}:")
    detail = httpx.get(f"{API}/reviews/{first}").json()
    for section in ("summary", "strengths", "major_issues", "minor_issues"):
        body = detail.get(section, "").strip()
        if body:
            print(f"  -- {section} --")
            print(f"    {body[:300]}")


if __name__ == "__main__":
    main()
