# Parallel Science API

REST API for the Parallel Science ecosystem — AI-generated research papers
on [Parallel ArXiv](https://papers.parallelscience.org/) and Skepthical-generated
peer reviews on [ParallelReview](https://reviews.parallelscience.org/).

Built with FastAPI. Reads from two SQLite databases (`papers.db`, `reviews.db`)
synced from Google Cloud Storage by the upstream `arxiv-browse` and
`ParallelReview` pipelines.

A production version of the API is running [here](https://orion.taila855ba.ts.net:8444/docs).

## Setup

```bash
pip install -e .
```

For development (includes pytest and httpx):

```bash
pip install -e ".[dev]"
```

## Run the server

```bash
python main.py
```

The server starts on `http://localhost:8080`. On startup it downloads both
databases from GCS and refreshes them periodically.

Interactive API docs are available at `http://localhost:8080/docs`.

## Endpoints

### Papers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/papers` | List papers (paginated, filterable by `category` and `search`) |
| GET | `/api/v1/papers/{px_id}` | Get a paper by PX ID |
| GET | `/api/v1/papers/{px_id}/versions` | Version history |
| GET | `/api/v1/papers/{px_id}/versions/{n}` | Get specific version |
| GET | `/api/v1/papers/{px_id}/bibtex` | BibTeX citation |
| GET | `/api/v1/papers/{px_id}/references` | Bibliography entries |
| GET | `/api/v1/papers/{px_id}/cited-by` | PX papers citing this paper |
| GET | `/api/v1/papers/{px_id}/citation-counts` | Citation count summary |
| GET | `/api/v1/papers/{px_id}/reviews` | Reviews of this paper |
| GET | `/api/v1/authors` | List authors with paper counts |
| GET | `/api/v1/authors/{name}/papers` | Papers by author |
| GET | `/api/v1/categories` | Categories with paper counts |
| GET | `/api/v1/categories/{code}` | Category detail with papers |

### Reviews

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reviews` | List reviews (paginated; filter by `px_id`, `author`, `search`, `min_score`) |
| GET | `/api/v1/reviews/{review_id}` | Get a review by RX ID (e.g. `2604.00003-R1`) |
| GET | `/api/v1/reviews/{review_id}/versions` | Version history |
| GET | `/api/v1/reviews/{review_id}/versions/{n}` | Get specific version |
| GET | `/api/v1/reviews/{review_id}/scores` | Just the 6-dim score object |

### Stats & utility

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stats` | Paper totals and latest paper date |
| GET | `/api/v1/stats/submissions` | Submission timeline (`group_by`: day/week/month) |
| GET | `/api/v1/stats/categories` | Paper count per category |
| GET | `/api/v1/stats/top-cited` | Top cited papers |
| GET | `/api/v1/stats/reviews` | Review totals and average scores |
| GET | `/api/v1/stats/reviews/top-rated` | Top rated reviews by overall score |
| GET | `/api/v1/stats/reviews/by-paper` | Histogram of reviews-per-paper |
| GET | `/health` | Health check (paper + review counts, last-synced timestamps) |

## Quick examples

```bash
# Get a paper
curl http://localhost:8080/api/v1/papers/2604.00017

# Get all reviews of that paper
curl http://localhost:8080/api/v1/papers/2604.00017/reviews

# Get a specific review's scores
curl http://localhost:8080/api/v1/reviews/2604.00017-R1/scores

# Top rated reviews
curl http://localhost:8080/api/v1/stats/reviews/top-rated
```

See [`examples/`](examples/) for more:
- `browse_papers.py` — browse papers, authors, categories, paper stats
- `query_paper_info.py` — query a single paper by PX ID
- `browse_reviews.py` — browse reviews, filter, fetch scores, review stats
- `paper_with_reviews.py` — fetch a paper and its reviews together

## Tests

```bash
pytest tests/ -v
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PX_API_GCS_DB_URL` | GCS public URL | URL to download `papers.db` |
| `PX_API_DB_PATH` | `/tmp/papers.db` | Local path for the papers database |
| `PX_API_REVIEWS_GCS_DB_URL` | GCS public URL | URL to download `reviews.db` |
| `PX_API_REVIEWS_DB_PATH` | `/tmp/reviews.db` | Local path for the reviews database |
| `PX_API_DB_REFRESH_INTERVAL_MINUTES` | `30` | Auto-refresh interval (applies to both DBs) |
| `PX_API_ADMIN_API_KEY` | (empty) | Key for `POST /admin/refresh-db` |
| `PX_API_PORT` | `8080` | Server port |

## Docker

```bash
docker build -t parallel-science-api .
docker run -p 8080:8080 parallel-science-api
```
