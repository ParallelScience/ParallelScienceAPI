"""Paper endpoints."""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.dependencies import PaginationParams, get_db, pagination, row_to_dict
from app.models import (
    PaginatedPapersResponse,
    PaperDetail,
    PaperVersion,
)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=PaginatedPapersResponse)
def list_papers(
    db=Depends(get_db),
    pag: PaginationParams = Depends(pagination),
    category: str | None = Query(None, description="Filter by category code (e.g. cs.AI) or archive (e.g. cs)"),
    search: str | None = Query(None, description="Search in title and abstract"),
):
    where = ["is_current = 1"]
    params: list = []

    if category:
        # Match exact category or archive prefix in primary or secondary
        where.append(
            "(primary_category = ? OR primary_category LIKE ? || '.%' "
            "OR secondary_categories LIKE '%\"' || ? || '\"%')"
        )
        params.extend([category, category, category])

    if search:
        where.append("(title LIKE ? OR abstract LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term])

    where_clause = " AND ".join(where)

    count = db.execute(
        f"SELECT COUNT(*) FROM papers WHERE {where_clause}", params
    ).fetchone()[0]

    rows = db.execute(
        f"SELECT * FROM papers WHERE {where_clause} ORDER BY date DESC LIMIT ? OFFSET ?",
        params + [pag.per_page, pag.offset],
    ).fetchall()

    return {
        "papers": [row_to_dict(r) for r in rows],
        "pagination": pag.meta(count),
    }


@router.get("/{px_id}", response_model=PaperDetail)
def get_paper(px_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM papers WHERE px_id = ? AND is_current = 1", (px_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Paper {px_id} not found")
    return row_to_dict(row)


@router.get("/{px_id}/versions", response_model=list[PaperVersion])
def get_versions(px_id: str, db=Depends(get_db)):
    rows = db.execute(
        "SELECT version, date, scraped_at, is_current, content_hash "
        "FROM papers WHERE px_id = ? ORDER BY version",
        (px_id,),
    ).fetchall()
    if not rows:
        raise HTTPException(404, f"Paper {px_id} not found")
    return [dict(r) for r in rows]


@router.get("/{px_id}/versions/{version}", response_model=PaperDetail)
def get_paper_version(px_id: str, version: int, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM papers WHERE px_id = ? AND version = ?", (px_id, version)
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Paper {px_id} version {version} not found")
    return row_to_dict(row)


@router.get("/{px_id}/bibtex", response_class=Response)
def get_bibtex(px_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM papers WHERE px_id = ? AND is_current = 1", (px_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Paper {px_id} not found")
    paper = row_to_dict(row)
    bibtex = _paper_to_bibtex(paper)
    return Response(content=bibtex, media_type="text/plain")


def _paper_to_bibtex(paper: dict) -> str:
    """Generate a BibTeX entry from a paper dict."""
    date = paper.get("date", "")
    match = re.match(r"(\d{4})-(\d{2})", date)
    year = match.group(1) if match else "2026"
    month_num = int(match.group(2)) if match else 1
    months = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]
    month = months[month_num - 1] if 1 <= month_num <= 12 else "jan"
    px_id = paper.get("px_id", "unknown")
    version = paper.get("version", 1)
    version_suffix = f"v{version}" if version > 1 else ""
    return (
        f"@article{{PX:{px_id},\n"
        f"  title   = {{{paper.get('title', '')}}},\n"
        f"  author  = {{{paper.get('author', '')}}},\n"
        f"  year    = {{{year}}},\n"
        f"  month   = {{{month}}},\n"
        f"  url     = {{https://papers.parallelscience.org/abs/{px_id}}},\n"
        f"  eprint  = {{{px_id}{version_suffix}}},\n"
        f"  archivePrefix = {{ParallelArXiv}},\n"
        f"  primaryClass  = {{{paper.get('primary_category', '')}}},\n"
        f"  journal = {{Parallel ArXiv}}\n"
        f"}}\n"
    )
