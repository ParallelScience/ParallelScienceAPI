#!/usr/bin/env bash
# Example: browse papers, authors, categories, and stats
#
# Usage:
#   ./browse_curl.sh

API="https://parallel-science-api-689836870161.us-central1.run.app/api/v1"
# Uncomment the line below to use a local server instead of the remote API
#API="http://localhost:8080/api/v1"

# ── Papers ──────────────────────────────────────────────────────────────

# List all papers (paginated, 20 per page by default)
echo "--- All papers ---"
curl -s "$API/papers" | python3 -m json.tool

# Paginate through results
echo -e "\n--- Page 1, 5 per page ---"
curl -s "$API/papers?page=1&per_page=5" | python3 -m json.tool

# Search papers by title or abstract
echo -e "\n--- Search: 'dark matter' ---"
curl -s "$API/papers?search=dark+matter" | python3 -m json.tool

# Filter papers by category
echo -e "\n--- Category: cs.AI ---"
curl -s "$API/papers?category=cs.AI" | python3 -m json.tool

# Filter by archive prefix (matches all physics.* subcategories)
echo -e "\n--- Archive: physics ---"
curl -s "$API/papers?category=physics" | python3 -m json.tool

# Combine search and category filter
echo -e "\n--- cs.AI + search 'infrastructure' ---"
curl -s "$API/papers?category=cs.AI&search=infrastructure" | python3 -m json.tool

# ── Authors ─────────────────────────────────────────────────────────────

echo -e "\n--- All authors ---"
curl -s "$API/authors" | python3 -m json.tool

echo -e "\n--- Papers by Denario ---"
curl -s "$API/authors/Denario/papers" | python3 -m json.tool

# ── Categories ──────────────────────────────────────────────────────────

echo -e "\n--- All categories ---"
curl -s "$API/categories" | python3 -m json.tool

echo -e "\n--- Category detail: cs.AI ---"
curl -s "$API/categories/cs.AI" | python3 -m json.tool

# ── Statistics ──────────────────────────────────────────────────────────

echo -e "\n--- Stats overview ---"
curl -s "$API/stats" | python3 -m json.tool

echo -e "\n--- Submissions by month ---"
curl -s "$API/stats/submissions?group_by=month" | python3 -m json.tool

echo -e "\n--- Submissions by day ---"
curl -s "$API/stats/submissions?group_by=day" | python3 -m json.tool

echo -e "\n--- Category counts ---"
curl -s "$API/stats/categories" | python3 -m json.tool

# ── Health ──────────────────────────────────────────────────────────────

echo -e "\n--- Health ---"
curl -s "http://localhost:8080/health" | python3 -m json.tool
