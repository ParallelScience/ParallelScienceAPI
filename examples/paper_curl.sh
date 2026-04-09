#!/usr/bin/env bash
# Example: query a single paper from the Parallel ArXiv API
#
# Usage:
#   ./paper_curl.sh              # uses default PX ID
#   ./paper_curl.sh 2604.00003   # specify a PX ID

API="http://localhost:8080/api/v1"
PX_ID="${1:-2604.00017}"

echo "=== Paper: $PX_ID ==="

# Get paper details (current version)
echo -e "\n--- Details ---"
curl -s "$API/papers/$PX_ID" | python3 -m json.tool

# Version history
echo -e "\n--- Versions ---"
curl -s "$API/papers/$PX_ID/versions" | python3 -m json.tool

# Specific version (v1)
echo -e "\n--- Version 1 ---"
curl -s "$API/papers/$PX_ID/versions/1" | python3 -m json.tool

# BibTeX citation
echo -e "\n--- BibTeX ---"
curl -s "$API/papers/$PX_ID/bibtex"
