# py-scrape-kit

> Scraping framework: retry, cache, rate-limit, pagination and CSV/JSON/SQLite export.

[![CI](https://github.com/dblzroch/py-scrape-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/dblzroch/py-scrape-kit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](pyproject.toml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Lightweight scraping toolkit built on `httpx`. Fetch pages with retry, per-domain
rate-limiting, optional disk cache, and export results to CSV, JSON or SQLite.

## Quickstart

```bash
# Clone
git clone https://github.com/dblzroch/py-scrape-kit.git
cd py-scrape-kit

# Install (uv)
uv sync --dev

# Fetch a single page
uv run scrape-kit fetch https://example.com

# Fetch with rate limit and cache
uv run scrape-kit fetch https://example.com --rate 1.0 --cache

# Export results
uv run scrape-kit export results.json --format json
```

## Commands

| Command | Description |
|---|---|
| `scrape-kit fetch <url> [--rate N] [--cache] [--retries N]` | Fetch one URL |
| `scrape-kit export <file> [--format csv|json|sqlite]` | Export last results |
| `scrape-kit paginate <base-url> <page-param> [--max-pages N]` | Walk paginated listings |

## How it works

- **HTTP client**: [httpx](https://www.python-httpx.org/) with retry and timeouts.
- **Rate limit**: per-domain token bucket, configurable requests/second.
- **Cache**: optional SQLite disk cache keyed by URL.
- **Pagination**: follows `?page=N` or custom page param up to a limit.
- **Export**: CSV, JSON or SQLite via `pydantic` models.
- **Tests**: `pytest` + `respx` (mocked HTTP), coverage gate at 80%.
- **CI**: GitHub Actions runs ruff, mypy and pytest on every push/PR.

## Tests & quality

```bash
make test      # pytest with coverage
make lint      # ruff + mypy
make fmt       # ruff format
```

## License

MIT
