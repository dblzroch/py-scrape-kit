"""HTTP client with retry, per-domain rate-limit and optional disk cache."""

import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import httpx

from py_scrape_kit.models import ScrapeRequest, ScrapeResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple token bucket rate limiter per domain."""

    def __init__(self, rate_per_second: float = 1.0):
        self.min_interval = 1.0 / rate_per_second if rate_per_second > 0 else 0
        self._last_call: dict[str, float] = {}

    def wait(self, domain: str) -> None:
        """Block until the domain's rate budget allows another call."""
        if self.min_interval <= 0:
            return
        now = time.monotonic()
        last = self._last_call.get(domain, 0.0)
        elapsed = now - last
        if elapsed < self.min_interval:
            sleep_for = self.min_interval - elapsed
            time.sleep(sleep_for)
            now = time.monotonic()
        self._last_call[domain] = now


class HttpClient:
    """Fetch URLs with retry, rate-limit and optional cache."""

    def __init__(
        self,
        rate_per_second: float = 1.0,
        retries: int = 3,
        timeout: float = 10.0,
        cache_path: Path | None = None,
    ):
        self.rate_limiter = RateLimiter(rate_per_second)
        self.retries = retries
        self.timeout = timeout
        self.cache_path = cache_path
        self._cache_conn: sqlite3.Connection | None = None
        if cache_path is not None:
            self._init_cache(cache_path)

    def _init_cache(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_conn = sqlite3.connect(path)
        self._cache_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                url TEXT PRIMARY KEY,
                status_code INTEGER,
                content TEXT,
                headers TEXT,
                fetched_at TEXT
            )
            """
        )
        self._cache_conn.commit()

    def _domain(self, url: str) -> str:
        from urllib.parse import urlparse

        return urlparse(url).netloc

    def _cache_get(self, url: str) -> ScrapeResponse | None:
        if self._cache_conn is None:
            return None
        row = self._cache_conn.execute(
            "SELECT status_code, content, headers, fetched_at FROM cache WHERE url = ?",
            (url,),
        ).fetchone()
        if row is None:
            return None
        return ScrapeResponse(
            url=url,
            status_code=row[0],
            content=row[1],
            headers={},
            fetched_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now(),
        )

    def _cache_put(self, response: ScrapeResponse) -> None:
        if self._cache_conn is None:
            return
        self._cache_conn.execute(
            "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?, ?)",
            (
                response.url,
                response.status_code,
                response.content,
                "{}",
                response.fetched_at.isoformat(),
            ),
        )
        self._cache_conn.commit()

    def fetch(self, request: ScrapeRequest) -> ScrapeResponse:
        """Fetch a single URL with retry and optional cache."""

        cached = self._cache_get(request.url)
        if cached is not None:
            logger.info("Cache hit: %s", request.url)
            return cached

        domain = self._domain(request.url)
        last_error: str | None = None

        for attempt in range(1, self.retries + 1):
            try:
                self.rate_limiter.wait(domain)
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(
                        request.url,
                        headers=request.headers,
                        params=request.params,
                    )
                response = ScrapeResponse(
                    url=request.url,
                    status_code=resp.status_code,
                    content=resp.text,
                    headers=dict(resp.headers),
                )
                self._cache_put(response)
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.warning(
                    "Attempt %d/%d failed for %s: %s",
                    attempt,
                    self.retries,
                    request.url,
                    last_error,
                )
                if attempt < self.retries:
                    time.sleep(0.5 * attempt)

        return ScrapeResponse(
            url=request.url,
            status_code=0,
            content="",
            error=last_error or "unknown error",
        )

    def fetch_many(self, requests: list[ScrapeRequest]) -> list[ScrapeResponse]:
        """Fetch multiple URLs sequentially."""
        return [self.fetch(req) for req in requests]

    def close(self) -> None:
        if self._cache_conn is not None:
            self._cache_conn.close()
            self._cache_conn = None
