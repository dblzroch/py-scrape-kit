"""Domain models for py-scrape-kit."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ScrapeRequest:
    """A single HTTP request to be fetched."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class ScrapeResponse:
    """Result of fetching one URL."""

    url: str
    status_code: int
    content: str
    headers: dict[str, str] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300 and self.error is None


@dataclass
class ScrapeResult:
    """Aggregated result of a scraping run."""

    requests: list[ScrapeRequest] = field(default_factory=list)
    responses: list[ScrapeResponse] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.responses)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.responses if r.ok)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.responses if not r.ok)

    def add(self, request: ScrapeRequest, response: ScrapeResponse) -> None:
        self.requests.append(request)
        self.responses.append(response)

    def to_dict_list(self) -> list[dict[str, object]]:
        return [
            {
                "url": r.url,
                "status_code": r.status_code,
                "ok": r.ok,
                "fetched_at": r.fetched_at.isoformat(),
                "error": r.error or "",
            }
            for r in self.responses
        ]

    def export_csv(self, path: Path) -> None:
        """Export results to a CSV file."""
        import csv

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["url", "status_code", "ok", "fetched_at", "error"],
            )
            writer.writeheader()
            writer.writerows(self.to_dict_list())

    def export_json(self, path: Path) -> None:
        """Export results to a JSON file."""
        import json

        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict_list(), handle, indent=2, ensure_ascii=False)

    def export_sqlite(self, path: Path) -> None:
        """Export results to a SQLite database."""
        import sqlite3

        conn = sqlite3.connect(path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    url TEXT,
                    status_code INTEGER,
                    ok INTEGER,
                    fetched_at TEXT,
                    error TEXT
                )
                """
            )
            conn.executemany(
                "INSERT INTO responses VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        row["url"],
                        row["status_code"],
                        1 if row["ok"] else 0,
                        row["fetched_at"],
                        row["error"],
                    )
                    for row in self.to_dict_list()
                ],
            )
            conn.commit()
        finally:
            conn.close()
