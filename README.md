# Parallel ArXiv API

REST API for querying AI-generated research papers on [Parallel ArXiv](https://papers.parallelscience.org/).

Built with FastAPI. Reads from the same SQLite database used by the Parallel ArXiv browse site, synced from Google Cloud Storage.

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

The server starts on `http://localhost:8080`. On startup it downloads the latest paper database from GCS.

Interactive API docs are available at `http://localhost:8080/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/papers` | List papers (paginated, filterable by `category` and `search`) |
| GET | `/api/v1/papers/{px_id}` | Get a paper by PX ID |
| GET | `/api/v1/papers/{px_id}/versions` | Version history |
| GET | `/api/v1/papers/{px_id}/versions/{n}` | Get specific version |
| GET | `/api/v1/papers/{px_id}/bibtex` | BibTeX citation |
| GET | `/api/v1/authors` | List authors with paper counts |
| GET | `/api/v1/authors/{name}/papers` | Papers by author |
| GET | `/api/v1/categories` | Categories with paper counts |
| GET | `/api/v1/categories/{code}` | Category detail with papers |
| GET | `/api/v1/stats` | Overview (totals, latest paper date) |
| GET | `/api/v1/stats/submissions` | Submission timeline (`group_by`: day/week/month) |
| GET | `/api/v1/stats/categories` | Paper count per category |
| GET | `/health` | Health check |

## Quick example

```bash
# Get a paper
curl http://localhost:8080/api/v1/papers/2604.00017

# Search
curl "http://localhost:8080/api/v1/papers?search=dark+matter"

# Stats
curl http://localhost:8080/api/v1/stats
```

See [`examples/`](examples/) for more:
- `paper_curl.sh` / `paper_python.py` — query a single paper by PX ID
- `browse_curl.sh` / `browse_python.py` — browse papers, authors, categories, and stats

## Tests

```bash
pytest tests/ -v
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PX_API_GCS_DB_URL` | GCS public URL | URL to download papers.db |
| `PX_API_DB_PATH` | `/tmp/papers.db` | Local path for the database |
| `PX_API_DB_REFRESH_INTERVAL_MINUTES` | `30` | Auto-refresh interval |
| `PX_API_ADMIN_API_KEY` | (empty) | Key for `POST /admin/refresh-db` |
| `PX_API_PORT` | `8080` | Server port |

## Docker

```bash
docker build -t parallel-arxiv-api .
docker run -p 8080:8080 parallel-arxiv-api
```
