"""Load and cache the arXiv taxonomy JSON."""

import json
import os

_taxonomy: dict | None = None
_TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "arxiv_taxonomy.json")


def get_taxonomy() -> dict:
    global _taxonomy
    if _taxonomy is None:
        if os.path.exists(_TAXONOMY_PATH):
            with open(_TAXONOMY_PATH) as f:
                _taxonomy = json.load(f)
        else:
            _taxonomy = {}
    return _taxonomy


def get_category_name(code: str) -> str:
    """Return the human-readable name for a category code, or the code itself."""
    tax = get_taxonomy()
    if code in tax:
        return tax[code].get("name", code)
    return code
