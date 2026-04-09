#!/usr/bin/env bash
# Example: querying the Parallel ArXiv API with curl
#
# Start the server first:
#   cd ParallelArxivAPI && python main.py
#
# The API docs are available at http://localhost:8080/docs

API="http://localhost:8080/api/v1"

# ── Papers ──────────────────────────────────────────────────────────────

# Get a paper by its PX ID (returns the current version)
curl -s "$API/papers/2604.00017" | python3 -m json.tool

# List all papers (paginated, 20 per page by default)
curl -s "$API/papers" | python3 -m json.tool

# Paginate through results
curl -s "$API/papers?page=1&per_page=5" | python3 -m json.tool

# Search papers by title or abstract
curl -s "$API/papers?search=Parallel+Science" | python3 -m json.tool

# Filter papers by category
curl -s "$API/papers?category=cs.AI" | python3 -m json.tool

# Filter by archive prefix (matches all physics.* subcategories)
curl -s "$API/papers?category=physics" | python3 -m json.tool

# Combine search and category filter
curl -s "$API/papers?category=cs.AI&search=infrastructure" | python3 -m json.tool

# ── Versions ────────────────────────────────────────────────────────────

# Get the full version history of a paper
curl -s "$API/papers/2604.00017/versions" | python3 -m json.tool

# Get a specific version
curl -s "$API/papers/2604.00017/versions/1" | python3 -m json.tool

# ── BibTeX ──────────────────────────────────────────────────────────────

# Get a BibTeX citation (returns text/plain)
curl -s "$API/papers/2604.00017/bibtex"

# ── Authors ─────────────────────────────────────────────────────────────

# List all authors with paper counts
curl -s "$API/authors" | python3 -m json.tool

# Get all papers by a specific author
curl -s "$API/authors/Denario/papers" | python3 -m json.tool

# ── Categories ──────────────────────────────────────────────────────────

# List all categories with paper counts
curl -s "$API/categories" | python3 -m json.tool

# Get papers in a specific category
curl -s "$API/categories/cs.AI" | python3 -m json.tool

# ── Statistics ──────────────────────────────────────────────────────────

# Overview: total papers, authors, categories
curl -s "$API/stats" | python3 -m json.tool

# Submission timeline (grouped by month, week, or day)
curl -s "$API/stats/submissions?group_by=month" | python3 -m json.tool
curl -s "$API/stats/submissions?group_by=day" | python3 -m json.tool

# Paper count per category
curl -s "$API/stats/categories" | python3 -m json.tool

# ── Health ──────────────────────────────────────────────────────────────

curl -s "http://localhost:8080/health" | python3 -m json.tool
