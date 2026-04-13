"""Review endpoints — Skepthical-generated peer reviews from ParallelReview."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import PaginationParams, get_reviews_db, pagination
from app.models import (
    PaginatedReviewsResponse,
    ReviewDetail,
    ReviewScores,
    ReviewSummary,
    ReviewVersion,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


_SUMMARY_COLUMNS = (
    "review_id, version, px_id, paper_title, paper_author, review_date, "
    "reviewer, pages_url, total_cost, "
    "score_overall, score_soundness, score_novelty, score_significance, "
    "score_clarity, score_evidence, score_justification"
)


def _scores_from_row(d: dict) -> ReviewScores:
    return ReviewScores(
        overall=d.get("score_overall"),
        soundness=d.get("score_soundness"),
        novelty=d.get("score_novelty"),
        significance=d.get("score_significance"),
        clarity=d.get("score_clarity"),
        evidence=d.get("score_evidence"),
        justification=d.get("score_justification") or "",
    )


def _row_to_summary(row: sqlite3.Row) -> dict:
    d = dict(row)
    return {
        "review_id": d["review_id"],
        "version": d["version"],
        "px_id": d["px_id"],
        "paper_title": d["paper_title"],
        "paper_author": d["paper_author"],
        "review_date": d["review_date"],
        "reviewer": d["reviewer"],
        "pages_url": d["pages_url"],
        "scores": _scores_from_row(d),
        "total_cost": d.get("total_cost"),
    }


def _row_to_detail(row: sqlite3.Row) -> dict:
    d = dict(row)
    base = _row_to_summary(row)
    base.update({
        "summary": d.get("summary", ""),
        "strengths": d.get("strengths", ""),
        "major_issues": d.get("major_issues", ""),
        "minor_issues": d.get("minor_issues", ""),
        "very_minor_issues": d.get("very_minor_issues", ""),
        "maths_audit": d.get("maths_audit", ""),
        "numerics_audit": d.get("numerics_audit", ""),
        "github_url": d.get("github_url", ""),
        "review_pdf_url": d.get("review_pdf_url", ""),
        "paper_pdf_url": d.get("paper_pdf_url", ""),
        "paper_pages_url": d.get("paper_pages_url", ""),
        "repo": d.get("repo", ""),
        "is_current": d.get("is_current", 0),
        "scraped_at": d.get("scraped_at", ""),
        "content_hash": d.get("content_hash"),
    })
    return base


@router.get("", response_model=PaginatedReviewsResponse)
def list_reviews(
    db=Depends(get_reviews_db),
    pag: PaginationParams = Depends(pagination),
    px_id: str | None = Query(None, description="Filter by paper PX ID"),
    author: str | None = Query(None, description="Filter by paper author (case-insensitive)"),
    search: str | None = Query(None, description="Search in paper title and summary"),
    min_score: int | None = Query(None, ge=1, le=10, description="Minimum overall score"),
):
    where = ["is_current = 1"]
    params: list = []

    if px_id:
        where.append("px_id = ?")
        params.append(px_id)

    if author:
        where.append("lower(paper_author) = lower(?)")
        params.append(author)

    if search:
        where.append("(paper_title LIKE ? OR summary LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term])

    if min_score is not None:
        where.append("score_overall IS NOT NULL AND score_overall >= ?")
        params.append(min_score)

    where_clause = " AND ".join(where)

    count = db.execute(
        f"SELECT COUNT(*) FROM reviews WHERE {where_clause}", params
    ).fetchone()[0]

    rows = db.execute(
        f"SELECT {_SUMMARY_COLUMNS} FROM reviews WHERE {where_clause} "
        "ORDER BY review_date DESC LIMIT ? OFFSET ?",
        params + [pag.per_page, pag.offset],
    ).fetchall()

    return {
        "reviews": [_row_to_summary(r) for r in rows],
        "pagination": pag.meta(count),
    }


@router.get("/{review_id}", response_model=ReviewDetail)
def get_review(review_id: str, db=Depends(get_reviews_db)):
    row = db.execute(
        "SELECT * FROM reviews WHERE review_id = ? AND is_current = 1",
        (review_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Review {review_id} not found")
    return _row_to_detail(row)


@router.get("/{review_id}/versions", response_model=list[ReviewVersion])
def get_review_versions(review_id: str, db=Depends(get_reviews_db)):
    rows = db.execute(
        "SELECT version, review_date, scraped_at, is_current, content_hash "
        "FROM reviews WHERE review_id = ? ORDER BY version",
        (review_id,),
    ).fetchall()
    if not rows:
        raise HTTPException(404, f"Review {review_id} not found")
    return [dict(r) for r in rows]


@router.get("/{review_id}/versions/{version}", response_model=ReviewDetail)
def get_review_version(review_id: str, version: int, db=Depends(get_reviews_db)):
    row = db.execute(
        "SELECT * FROM reviews WHERE review_id = ? AND version = ?",
        (review_id, version),
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Review {review_id} version {version} not found")
    return _row_to_detail(row)


@router.get("/{review_id}/scores", response_model=ReviewScores)
def get_review_scores(review_id: str, db=Depends(get_reviews_db)):
    row = db.execute(
        "SELECT score_overall, score_soundness, score_novelty, score_significance, "
        "score_clarity, score_evidence, score_justification "
        "FROM reviews WHERE review_id = ? AND is_current = 1",
        (review_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Review {review_id} not found")
    return _scores_from_row(dict(row))
