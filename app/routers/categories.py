"""Category endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import PaginationParams, get_db, pagination, row_to_dict
from app.models import CategoryDetail, CategorySummary
from app.taxonomy import get_category_name

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategorySummary])
def list_categories(db=Depends(get_db)):
    rows = db.execute(
        "SELECT primary_category AS code, COUNT(*) AS paper_count "
        "FROM papers WHERE is_current = 1 "
        "GROUP BY primary_category ORDER BY paper_count DESC"
    ).fetchall()

    return [
        {
            "code": r["code"],
            "name": get_category_name(r["code"]),
            "paper_count": r["paper_count"],
        }
        for r in rows
    ]


@router.get("/{category_code}", response_model=CategoryDetail)
def get_category(
    category_code: str,
    db=Depends(get_db),
    pag: PaginationParams = Depends(pagination),
):
    # Count papers matching this category (primary or secondary, or archive prefix)
    count = db.execute(
        "SELECT COUNT(*) FROM papers WHERE is_current = 1 AND "
        "(primary_category = ? OR primary_category LIKE ? || '.%' "
        "OR secondary_categories LIKE '%\"' || ? || '\"%')",
        (category_code, category_code, category_code),
    ).fetchone()[0]

    if count == 0:
        raise HTTPException(404, f"Category {category_code} not found or has no papers")

    rows = db.execute(
        "SELECT * FROM papers WHERE is_current = 1 AND "
        "(primary_category = ? OR primary_category LIKE ? || '.%' "
        "OR secondary_categories LIKE '%\"' || ? || '\"%') "
        "ORDER BY date DESC LIMIT ? OFFSET ?",
        (category_code, category_code, category_code, pag.per_page, pag.offset),
    ).fetchall()

    return {
        "code": category_code,
        "name": get_category_name(category_code),
        "papers": [row_to_dict(r) for r in rows],
        "pagination": pag.meta(count),
    }
