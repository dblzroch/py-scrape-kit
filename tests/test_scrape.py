"""Tests for py-scrape-kit client, models, paginator and CLI."""

import json
import sqlite3

import httpx
from typer.testing import CliRunner

from py_scrape_kit.cli import app
from py_scrape_kit.client import HttpClient, RateLimiter
from py_scrape_kit.models import ScrapeRequest, ScrapeResponse, ScrapeResult
from py_scrape_kit.paginator import paginate


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
def test_scrape_response_ok():
    resp = ScrapeResponse(
        url="https://example.com", status_code=200, content="<html></html>"
    )
    assert resp.ok is True


def test_scrape_response_error():
    resp = ScrapeResponse(
        url="https://example.com", status_code=500, content="", error="boom"
    )
    assert resp.ok is False


def test_scrape_result_counts():
    result = ScrapeResult()
    result.add(
        ScrapeRequest(url="https://a.com"),
        ScrapeResponse(url="https://a.com", status_code=200, content="ok"),
    )
    result.add(
        ScrapeRequest(url="https://b.com"),
        ScrapeResponse(url="https://b.com", status_code=500, content="", error="x"),
    )
    assert result.total == 2
    assert result.succeeded == 1
    assert result.failed == 1


def test_scrape_result_export_csv(tmp_path):
    result = ScrapeResult()
    result.add(
        ScrapeRequest(url="https://a.com"),
        ScrapeResponse(url="https://a.com", status_code=200, content="ok"),
    )
    path = tmp_path / "out.csv"
    result.export_csv(path)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "https://a.com" in content


def test_scrape_result_export_json(tmp_path):
    result = ScrapeResult()
    result.add(
        ScrapeRequest(url="https://a.com"),
        ScrapeResponse(url="https://a.com", status_code=200, content="ok"),
    )
    path = tmp_path / "out.json"
    result.export_json(path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["url"] == "https://a.com"


def test_scrape_result_export_sqlite(tmp_path):
    result = ScrapeResult()
    result.add(
        ScrapeRequest(url="https://a.com"),
        ScrapeResponse(url="https://a.com", status_code=200, content="ok"),
    )
    path = tmp_path / "out.sqlite"
    result.export_sqlite(path)
    assert path.exists()
    conn = sqlite3.connect(path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    finally:
        conn.close()
    assert count == 1


# ------------------------------------------------------------------
# RateLimiter
# ------------------------------------------------------------------
def test_rate_limiter_no_limit():
    limiter = RateLimiter(rate_per_second=0)
    limiter.wait("example.com")  # should not block


# ------------------------------------------------------------------
# HttpClient
# ------------------------------------------------------------------
def test_http_client_fetch_success(respx_mock):
    route = respx_mock.get("https://example.com").mock(
        return_value=httpx.Response(200, text="hello")
    )
    client = HttpClient(rate_per_second=0, retries=1, timeout=5)
    try:
        response = client.fetch(ScrapeRequest(url="https://example.com"))
        assert response.status_code == 200
        assert response.content == "hello"
        assert response.ok is True
        assert route.called
    finally:
        client.close()


def test_http_client_fetch_retry(respx_mock):
    respx_mock.get("https://flaky.com").mock(side_effect=Exception("connection error"))
    client = HttpClient(rate_per_second=0, retries=2, timeout=5)
    try:
        response = client.fetch(ScrapeRequest(url="https://flaky.com"))
        assert response.status_code == 0
        assert response.ok is False
        assert response.error is not None
    finally:
        client.close()


def test_http_client_cache(tmp_path, respx_mock):
    cache_file = tmp_path / "cache.sqlite"
    client = HttpClient(rate_per_second=0, retries=1, timeout=5, cache_path=cache_file)
    try:
        # First call: no cache yet, use respx to mock
        respx_mock.get("https://cached.com").mock(
            return_value=httpx.Response(200, text="cached-content")
        )
        response1 = client.fetch(ScrapeRequest(url="https://cached.com"))
        assert response1.content == "cached-content"

        # Second call: should hit cache (respx route already consumed)
        response2 = client.fetch(ScrapeRequest(url="https://cached.com"))
        assert response2.content == "cached-content"
    finally:
        client.close()


# ------------------------------------------------------------------
# Paginator
# ------------------------------------------------------------------
def test_paginate_stops_on_error(respx_mock):
    respx_mock.get("https://example.com").mock(
        return_value=httpx.Response(500, text="error")
    )
    client = HttpClient(rate_per_second=0, retries=1, timeout=5)
    try:
        result = paginate(client, "https://example.com", page_param="page", max_pages=5)
        assert result.total == 1
        assert result.failed == 1
    finally:
        client.close()


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def test_cli_fetch(respx_mock):
    respx_mock.get("https://example.com").mock(
        return_value=httpx.Response(200, text="hello world")
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["fetch", "https://example.com", "--rate", "0", "--retries", "1"],
    )
    assert result.exit_code == 0
    assert "Status: 200" in result.output
    assert "hello world" in result.output


def test_cli_paginate(respx_mock):
    respx_mock.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="page 1")
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "paginate",
            "https://example.com/",
            "--page-param",
            "page",
            "--max-pages",
            "1",
            "--rate",
            "0",
            "--retries",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert "Pages fetched" in result.output


def test_cli_export_json(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["export", str(tmp_path / "out.json"), "--format", "json"]
    )
    assert result.exit_code == 0
    assert tmp_path.joinpath("out.json").exists()


def test_cli_export_unknown_format(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["export", str(tmp_path / "out.xml"), "--format", "xml"]
    )
    assert result.exit_code == 1
