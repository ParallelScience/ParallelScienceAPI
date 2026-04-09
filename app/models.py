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
    paper_count: int
    db_last_synced: str | None
