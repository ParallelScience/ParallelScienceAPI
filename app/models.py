"""Pydantic response models for the API."""

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class PaperSummary(BaseModel):
    px_id: str
    version: int
    title: str
    author: str
    date: str
    primary_category: str
    secondary_categories: list[str]
    abstract: str
    pdf_url: str
    pages_url: str


class PaperDetail(PaperSummary):
    repo: str
    github_url: str
    is_current: bool
    scraped_at: str
    content_hash: str | None


class PaginatedPapersResponse(BaseModel):
    papers: list[PaperSummary]
    pagination: PaginationMeta


class PaperVersion(BaseModel):
    version: int
    date: str
    scraped_at: str
    is_current: bool
    content_hash: str | None


class AuthorSummary(BaseModel):
    name: str
    paper_count: int


class PaginatedAuthorsResponse(BaseModel):
    authors: list[AuthorSummary]
    pagination: PaginationMeta


class CategorySummary(BaseModel):
    code: str
    name: str
    paper_count: int


class CategoryDetail(BaseModel):
    code: str
    name: str
    papers: list[PaperSummary]
    pagination: PaginationMeta


class StatsOverview(BaseModel):
    total_papers: int
    total_authors: int
    total_categories: int
    latest_paper_date: str | None


class SubmissionPoint(BaseModel):
    period: str
    count: int


class CategoryCount(BaseModel):
    category: str
    name: str
    count: int


class HealthResponse(BaseModel):
    status: str
    # None when that DB failed to load — status is then "degraded", and the
    # service still answers so the failure is visible instead of a blank 5xx.
    paper_count: int | None
    db_last_synced: str | None
    reviews_count: int | None
    reviews_last_synced: str | None


# --- Citations ---

class CitationEntry(BaseModel):
    citation_key: str
    cited_px_id: str | None
    arxiv_id: str | None
    doi: str | None
    title: str | None
    authors: str | None
    year: str | None
    is_px_paper: bool


class CitedByEntry(BaseModel):
    citing_px_id: str
    title: str
    author: str
    date: str
    primary_category: str


class CitationCounts(BaseModel):
    px_id: str
    references_count: int
    cited_by_count: int
    px_references_count: int
    external_cited_by_count: int


class ExternalCitedByEntry(BaseModel):
    source: str                      # 'arxiv' (room for 'biorxiv', 'medrxiv')
    external_id: str                 # e.g. '2604.12345'
    external_version: str | None
    title: str | None
    authors: str | None
    year: str | None
    match_method: str                # 'bib_archive_prefix' | 'bib_citation_key' | 'bib_url' | 'tex_regex'
    posted_date: str | None
    discovered_at: str


class TopCitedPaper(BaseModel):
    px_id: str
    title: str
    author: str
    cited_by_count: int


# --- Reviews ---

class ReviewScores(BaseModel):
    overall: int | None
    soundness: int | None
    novelty: int | None
    significance: int | None
    clarity: int | None
    evidence: int | None
    justification: str


class ReviewSummary(BaseModel):
    review_id: str
    version: int
    px_id: str
    paper_title: str
    paper_author: str
    review_date: str
    reviewer: str
    pages_url: str
    scores: ReviewScores
    total_cost: float | None


class ReviewDetail(ReviewSummary):
    summary: str
    strengths: str
    major_issues: str
    minor_issues: str
    very_minor_issues: str
    maths_audit: str
    numerics_audit: str
    github_url: str
    review_pdf_url: str
    paper_pdf_url: str
    paper_pages_url: str
    repo: str
    is_current: int
    scraped_at: str
    content_hash: str | None


class ReviewVersion(BaseModel):
    version: int
    review_date: str
    scraped_at: str
    is_current: int
    content_hash: str | None


class PaginatedReviewsResponse(BaseModel):
    reviews: list[ReviewSummary]
    pagination: PaginationMeta


class AverageReviewScores(BaseModel):
    overall: float | None
    soundness: float | None
    novelty: float | None
    significance: float | None
    clarity: float | None
    evidence: float | None


class ReviewStatsOverview(BaseModel):
    total_reviews: int
    total_papers_reviewed: int
    average_scores: AverageReviewScores
    latest_review_date: str | None


class TopRatedReview(BaseModel):
    review_id: str
    px_id: str
    paper_title: str
    paper_author: str
    score_overall: int


class ReviewsPerPaperBucket(BaseModel):
    reviews_per_paper: int
    paper_count: int
