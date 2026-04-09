"""Citation endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_db
from app.models import CitationCounts, CitationEntry, CitedByEntry

router = APIRouter(prefix="/papers", tags=["citations"])


@router.get("/{px_id}/references", response_model=list[CitationEntry])
def get_references(px_id: str, db=Depends(get_db)):
    """Get all bibliography entries for a paper."""
    paper = db.execute(
        "SELECT 1 FROM papers WHERE px_id = ? AND is_current = 1", (px_id,)
    ).fetchone()
    if not paper:
        raise HTTPException(404, f"Paper {px_id} not found")

    rows = db.execute(
        "SELECT citation_key, cited_px_id, arxiv_id, doi, title, authors, year "
        "FROM citations WHERE citing_px_id = ? ORDER BY citation_key",
        (px_id,),
    ).fetchall()
    return [
        {**dict(r), "is_px_paper": r["cited_px_id"] is not None}
        for r in rows
    ]


@router.get("/{px_id}/cited-by", response_model=list[CitedByEntry])
def get_cited_by(px_id: str, db=Depends(get_db)):
    """Get PX papers that cite this paper."""
    rows = db.execute(
        "SELECT c.citing_px_id, p.title, p.author, p.date, p.primary_category "
        "FROM citations c "
        "JOIN papers p ON p.px_id = c.citing_px_id AND p.is_current = 1 "
        "WHERE c.cited_px_id = ? "
        "ORDER BY p.date DESC",
        (px_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{px_id}/citation-counts", response_model=CitationCounts)
def get_citation_counts(px_id: str, db=Depends(get_db)):
    """Get citation count summary for a paper."""
    paper = db.execute(
        "SELECT 1 FROM papers WHERE px_id = ? AND is_current = 1", (px_id,)
    ).fetchone()
    if not paper:
        raise HTTPException(404, f"Paper {px_id} not found")

    refs = db.execute(
        "SELECT COUNT(*) AS total, "
        "COALESCE(SUM(CASE WHEN cited_px_id IS NOT NULL THEN 1 ELSE 0 END), 0) AS px_refs "
        "FROM citations WHERE citing_px_id = ?",
        (px_id,),
    ).fetchone()

    cited_by = db.execute(
        "SELECT COUNT(*) FROM citations WHERE cited_px_id = ?",
        (px_id,),
    ).fetchone()[0]

    return {
        "px_id": px_id,
        "references_count": refs["total"],
        "cited_by_count": cited_by,
        "px_references_count": refs["px_refs"],
    }
