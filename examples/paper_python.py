"""Example: query a single paper from the Parallel ArXiv API.

Usage:
    python paper_python.py              # uses default PX ID
    python paper_python.py 2604.00003   # specify a PX ID

Requires: pip install httpx
"""

import sys

import httpx

API = "http://localhost:8080/api/v1"


def main():
    px_id = sys.argv[1] if len(sys.argv) > 1 else "2604.00017"

    # ── Paper details ───────────────────────────────────────────────────
    paper = httpx.get(f"{API}/papers/{px_id}").json()
    print(f"Paper:    PX:{px_id}")
    print(f"Title:    {paper['title']}")
    print(f"Author:   {paper['author']}")
    print(f"Date:     {paper['date']}")
    print(f"Category: {paper['primary_category']}")
    if paper["secondary_categories"]:
        print(f"Also in:  {', '.join(paper['secondary_categories'])}")
    print(f"PDF:      {paper['pdf_url']}")
    print(f"Pages:    {paper['pages_url']}")
    print(f"GitHub:   {paper['github_url']}")
    print()

    # ── Version history ─────────────────────────────────────────────────
    versions = httpx.get(f"{API}/papers/{px_id}/versions").json()
    print(f"Versions ({len(versions)} total):")
    for v in versions:
        tag = " <- current" if v["is_current"] else ""
        print(f"  v{v['version']}  {v['date']}  (scraped {v['scraped_at']}){tag}")
    print()

    # ── Specific version ────────────────────────────────────────────────
    v1 = httpx.get(f"{API}/papers/{px_id}/versions/1").json()
    print(f"Version 1 title: {v1['title']}")
    print()

    # ── BibTeX ──────────────────────────────────────────────────────────
    bibtex = httpx.get(f"{API}/papers/{px_id}/bibtex").text
    print("BibTeX:")
    print(bibtex)


if __name__ == "__main__":
    main()
