"""Pagination helpers for py-scrape-kit."""

from py_scrape_kit.client import HttpClient
from py_scrape_kit.models import ScrapeRequest, ScrapeResult


def paginate(
    client: HttpClient,
    base_url: str,
    page_param: str = "page",
    max_pages: int = 10,
    start_page: int = 1,
    stop_when_empty: bool = True,
) -> ScrapeResult:
    """Walk a paginated listing by incrementing ``page_param``.

    Args:
        client: HTTP client to use for fetching.
        base_url: URL template or base URL.
        page_param: Query parameter name for the page number.
        max_pages: Safety cap on number of pages fetched.
        start_page: First page number to fetch.
        stop_when_empty: Stop when a page returns no content.

    Returns:
        Aggregated :class:`ScrapeResult`.
    """
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    result = ScrapeResult()

    for page in range(start_page, start_page + max_pages):
        parsed = urlparse(base_url)
        params = dict(parse_qsl(parsed.query))
        params[page_param] = str(page)
        url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(params),
                parsed.fragment,
            )
        )

        request = ScrapeRequest(url=url)
        response = client.fetch(request)
        result.add(request, response)

        if not response.ok:
            break

        if stop_when_empty and not response.content.strip():
            break

    return result


def paginate_links(
    client: HttpClient,
    start_url: str,
    link_selector: str = "a.next::attr(href)",
    max_pages: int = 10,
) -> ScrapeResult:
    """Walk pagination by following ``next`` links (placeholder).

    This is a placeholder for CSS-selector-based pagination. The actual
    HTML parsing would require an additional dependency (e.g. ``selectolax``
    or ``BeautifulSoup``). For now it fetches the start URL once.

    Args:
        client: HTTP client.
        start_url: First URL to fetch.
        link_selector: CSS selector for the next link (unused in placeholder).
        max_pages: Safety cap.

    Returns:
        Aggregated :class:`ScrapeResult`.
    """
    result = ScrapeResult()
    request = ScrapeRequest(url=start_url)
    response = client.fetch(request)
    result.add(request, response)
    return result
