"""CLI entry point for py-scrape-kit."""

from pathlib import Path

import typer

from py_scrape_kit.client import HttpClient
from py_scrape_kit.models import ScrapeRequest, ScrapeResult
from py_scrape_kit.paginator import paginate

app = typer.Typer(help="Scraping framework: retry, cache, rate-limit and export.")

_RATE_OPTION = typer.Option(
    1.0, "--rate", "-r", help="Requests per second (rate limit)."
)
_RETRIES_OPTION = typer.Option(3, "--retries", "-n", help="Number of retry attempts.")
_CACHE_OPTION = typer.Option(False, "--cache", "-c", help="Enable disk cache.")
_CACHE_PATH_OPTION = typer.Option(
    Path(".scrape-cache.sqlite"), "--cache-path", help="Path to cache database."
)


@app.command()
def fetch(
    url: str = typer.Argument(..., help="URL to fetch."),
    rate: float = _RATE_OPTION,
    retries: int = _RETRIES_OPTION,
    cache: bool = _CACHE_OPTION,
    cache_path: Path = _CACHE_PATH_OPTION,
) -> None:
    """Fetch a single URL."""
    client = HttpClient(
        rate_per_second=rate, retries=retries, cache_path=cache_path if cache else None
    )
    try:
        request = ScrapeRequest(url=url)
        response = client.fetch(request)

        typer.echo(f"URL: {response.url}")
        typer.echo(f"Status: {response.status_code}")
        typer.echo(f"OK: {response.ok}")
        if response.error:
            typer.echo(f"Error: {response.error}")
        typer.echo(f"Content length: {len(response.content)}")
        typer.echo(response.content[:500])
    finally:
        client.close()


@app.command(name="paginate")
def paginate_cmd(
    base_url: str = typer.Argument(..., help="Base URL to paginate."),
    page_param: str = typer.Option(
        "page", "--page-param", help="Query parameter name for page number."
    ),
    max_pages: int = typer.Option(10, "--max-pages", help="Maximum pages to fetch."),
    rate: float = _RATE_OPTION,
    retries: int = _RETRIES_OPTION,
    cache: bool = _CACHE_OPTION,
    cache_path: Path = _CACHE_PATH_OPTION,
) -> None:
    """Fetch paginated listings."""
    client = HttpClient(
        rate_per_second=rate, retries=retries, cache_path=cache_path if cache else None
    )
    try:
        result = paginate(client, base_url, page_param=page_param, max_pages=max_pages)
        typer.echo(f"Pages fetched: {result.total}")
        typer.echo(f"Succeeded: {result.succeeded}")
        typer.echo(f"Failed: {result.failed}")
        for resp in result.responses:
            typer.echo(
                f"  {resp.url} -> {resp.status_code} ({'ok' if resp.ok else 'error'})"
            )
    finally:
        client.close()


_PATH_ARG = typer.Argument(..., help="Output file path.")


@app.command()
def export(
    path: Path = _PATH_ARG,
    format: str = typer.Option(
        "json", "--format", "-f", help="Export format: csv, json or sqlite."
    ),
) -> None:
    """Export the last scrape result (placeholder)."""
    result = ScrapeResult()
    if format == "csv":
        result.export_csv(path)
    elif format == "json":
        result.export_json(path)
    elif format == "sqlite":
        result.export_sqlite(path)
    else:
        typer.echo(f"Unknown format: {format}")
        raise typer.Exit(code=1)
    typer.echo(f"Exported {result.total} results to {path} ({format})")


if __name__ == "__main__":
    app()
