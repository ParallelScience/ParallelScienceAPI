"""Statistics endpoints."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db
from app.models import CategoryCount, StatsOverview, SubmissionPoint
from app.taxonomy import get_category_name

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("", response_model=StatsOverview)
def get_stats(db=Depends(get_db)):
    row = db.execute(
        "SELECT COUNT(*) AS total_papers, "
        "COUNT(DISTINCT author) AS total_authors, "
        "COUNT(DISTINCT primary_category) AS total_categories, "
        "MAX(date) AS latest_paper_date "
        "FROM papers WHERE is_current = 1"
    ).fetchone()
    return dict(row)


@router.get("/submissions", response_model=list[SubmissionPoint])
def get_submissions(
    db=Depends(get_db),
    group_by: str = Query("month", pattern="^(day|week|month)$", description="Group by: day, week, or month"),
):
    if group_by == "day":
        expr = "substr(date, 1, 10)"
    elif group_by == "week":
        # ISO week: year + week number
        expr = "strftime('%Y-W%W', date)"
    else:
        expr = "substr(date, 1, 7)"

    rows = db.execute(
        f"SELECT {expr} AS period, COUNT(*) AS count "
        "FROM papers WHERE is_current = 1 "
        f"GROUP BY {expr} ORDER BY period"
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/categories", response_model=list[CategoryCount])
def get_category_stats(db=Depends(get_db)):
    rows = db.execute(
        "SELECT primary_category AS category, COUNT(*) AS count "
        "FROM papers WHERE is_current = 1 "
        "GROUP BY primary_category ORDER BY count DESC"
    ).fetchall()
    return [
        {
            "category": r["category"],
            "name": get_category_name(r["category"]),
            "count": r["count"],
        }
        for r in rows
    ]
