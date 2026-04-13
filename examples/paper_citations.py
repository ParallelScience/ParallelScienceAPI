"""Example: fetch a paper's bibliography and inspect cross-references to other PX papers.

Shows how to use the citation endpoints:
    /papers/{px_id}/references       — bibliography entries (all external refs)
    /papers/{px_id}/citation-counts  — totals (including px_references_count)
    /papers/{px_id}/cited-by         — PX papers that cite this one

Usage:
    python paper_citations.py [PX_ID]

Requires: pip install httpx
"""

import sys

import httpx

API = "https://parallel-science-api-689836870161.us-central1.run.app/api/v1"
# Uncomment the line below to use a local server instead of the remote API
#API = "http://localhost:8080/api/v1"


def main():
    px_id = sys.argv[1] if len(sys.argv) > 1 else "2604.00017"

    paper_resp = httpx.get(f"{API}/papers/{px_id}")
    if paper_resp.status_code == 404:
        print(f"Paper {px_id} not found")
        return
    paper = paper_resp.json()
    print(f"Paper: {paper['title']}")
    print(f"  Author: {paper['author']}")
    print(f"  Date:   {paper['date']}")
    print()

    counts = httpx.get(f"{API}/papers/{px_id}/citation-counts").json()
    print(
        f"Citation counts: references={counts['references_count']}  "
        f"px_references={counts['px_references_count']}  "
        f"cited_by={counts['cited_by_count']}"
    )
    print()

    refs = httpx.get(f"{API}/papers/{px_id}/references").json()
    if not refs:
        print("No bibliography extracted yet.")
        return

    px_refs = [r for r in refs if r.get("cited_px_id")]
    ext_refs = [r for r in refs if not r.get("cited_px_id")]

    if px_refs:
        print(f"Cross-references to Parallel ArXiv papers ({len(px_refs)}):")
        for r in px_refs:
            print(f"  {r['citation_key']} → PX:{r['cited_px_id']}")
            if r.get("title"):
                print(f"    {r['title'][:80]}")
        print()

    print(f"External references ({len(ext_refs)}):")
    for r in ext_refs[:10]:
        label = r.get("arxiv_id") or r.get("doi") or "—"
        title = (r.get("title") or "").strip()
        year = r.get("year") or ""
        print(f"  {r['citation_key']}  [{label}]  {year}  {title[:70]}")
    if len(ext_refs) > 10:
        print(f"  ... and {len(ext_refs) - 10} more")
    print()

    cited_by = httpx.get(f"{API}/papers/{px_id}/cited-by").json()
    if cited_by:
        print(f"Cited by ({len(cited_by)}):")
        for p in cited_by:
            print(f"  PX:{p['px_id']}  {p['title'][:80]}")
    else:
        print("Not yet cited by any Parallel ArXiv paper.")


if __name__ == "__main__":
    main()
