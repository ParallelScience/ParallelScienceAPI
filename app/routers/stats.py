"""Statistics endpoints."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, get_reviews_db
from app.models import (
    AverageReviewScores,
    CategoryCount,
    ReviewStatsOverview,
    ReviewsPerPaperBucket,
    StatsOverview,
    SubmissionPoint,
    TopCitedPaper,
    TopRatedReview,
)
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


@router.get("/top-cited", response_model=list[TopCitedPaper])
def get_top_cited(
    db=Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    """Papers most cited by other PX papers."""
    rows = db.execute(
        "SELECT c.cited_px_id AS px_id, p.title, p.author, COUNT(*) AS cited_by_count "
        "FROM citations c "
        "JOIN papers p ON p.px_id = c.cited_px_id AND p.is_current = 1 "
        "WHERE c.cited_px_id IS NOT NULL "
        "GROUP BY c.cited_px_id "
        "ORDER BY cited_by_count DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# --- Review stats -----------------------------------------------------------


@router.get("/reviews", response_model=ReviewStatsOverview)
def get_review_stats(reviews_db=Depends(get_reviews_db)):
    row = reviews_db.execute(
        "SELECT COUNT(*) AS total_reviews, "
        "COUNT(DISTINCT px_id) AS total_papers_reviewed, "
        "AVG(score_overall) AS avg_overall, "
        "AVG(score_soundness) AS avg_soundness, "
        "AVG(score_novelty) AS avg_novelty, "
        "AVG(score_significance) AS avg_significance, "
        "AVG(score_clarity) AS avg_clarity, "
        "AVG(score_evidence) AS avg_evidence, "
        "MAX(review_date) AS latest_review_date "
        "FROM reviews WHERE is_current = 1"
    ).fetchone()
    d = dict(row)
    return {
        "total_reviews": d["total_reviews"] or 0,
        "total_papers_reviewed": d["total_papers_reviewed"] or 0,
        "average_scores": AverageReviewScores(
            overall=d["avg_overall"],
            soundness=d["avg_soundness"],
            novelty=d["avg_novelty"],
            significance=d["avg_significance"],
            clarity=d["avg_clarity"],
            evidence=d["avg_evidence"],
        ),
        "latest_review_date": d["latest_review_date"],
    }


@router.get("/reviews/top-rated", response_model=list[TopRatedReview])
def get_top_rated_reviews(
    reviews_db=Depends(get_reviews_db),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    rows = reviews_db.execute(
        "SELECT review_id, px_id, paper_title, paper_author, score_overall "
        "FROM reviews WHERE is_current = 1 AND score_overall IS NOT NULL "
        "ORDER BY score_overall DESC, review_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/reviews/by-paper", response_model=list[ReviewsPerPaperBucket])
def get_reviews_per_paper(reviews_db=Depends(get_reviews_db)):
    """Histogram: how many papers have 1 review, 2 reviews, 3 reviews, etc."""
    rows = reviews_db.execute(
        "SELECT reviews_per_paper, COUNT(*) AS paper_count FROM ("
        "  SELECT px_id, COUNT(*) AS reviews_per_paper "
        "  FROM reviews WHERE is_current = 1 GROUP BY px_id"
        ") GROUP BY reviews_per_paper ORDER BY reviews_per_paper"
    ).fetchall()
    return [dict(r) for r in rows]
