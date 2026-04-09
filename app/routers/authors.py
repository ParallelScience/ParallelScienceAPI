"""Author endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies import PaginationParams, get_db, pagination, row_to_dict
from app.models import PaginatedAuthorsResponse, PaginatedPapersResponse

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=PaginatedAuthorsResponse)
def list_authors(
    db=Depends(get_db),
    pag: PaginationParams = Depends(pagination),
):
    count = db.execute(
        "SELECT COUNT(DISTINCT author) FROM papers WHERE is_current = 1"
    ).fetchone()[0]

    rows = db.execute(
        "SELECT author AS name, COUNT(*) AS paper_count "
        "FROM papers WHERE is_current = 1 "
        "GROUP BY author ORDER BY author "
        "LIMIT ? OFFSET ?",
        (pag.per_page, pag.offset),
    ).fetchall()

    return {
        "authors": [dict(r) for r in rows],
        "pagination": pag.meta(count),
    }


@router.get("/{author_name}/papers", response_model=PaginatedPapersResponse)
def get_author_papers(
    author_name: str,
    db=Depends(get_db),
    pag: PaginationParams = Depends(pagination),
):
    count = db.execute(
        "SELECT COUNT(*) FROM papers WHERE is_current = 1 AND lower(author) = lower(?)",
        (author_name,),
    ).fetchone()[0]

    rows = db.execute(
        "SELECT * FROM papers WHERE is_current = 1 AND lower(author) = lower(?) "
        "ORDER BY date DESC LIMIT ? OFFSET ?",
        (author_name, pag.per_page, pag.offset),
    ).fetchall()

    return {
        "papers": [row_to_dict(r) for r in rows],
        "pagination": pag.meta(count),
    }
