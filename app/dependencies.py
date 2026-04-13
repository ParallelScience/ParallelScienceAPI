"""FastAPI dependencies for database access and pagination."""

import json
import math
import sqlite3
from dataclasses import dataclass

from fastapi import Query

from app.database import get_connection


def get_papers_db() -> sqlite3.Connection:
    return get_connection("papers")


def get_reviews_db() -> sqlite3.Connection:
    return get_connection("reviews")


# Backwards-compatible alias — existing routers import `get_db`.
get_db = get_papers_db


@dataclass
class PaginationParams:
    page: int
    per_page: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def meta(self, total: int) -> dict:
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": total,
            "total_pages": max(1, math.ceil(total / self.per_page)),
        }


def pagination(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    return PaginationParams(page=page, per_page=per_page)


def row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a dict, parsing JSON fields."""
    d = dict(row)
    if isinstance(d.get("secondary_categories"), str):
        d["secondary_categories"] = json.loads(d["secondary_categories"])
    return d
