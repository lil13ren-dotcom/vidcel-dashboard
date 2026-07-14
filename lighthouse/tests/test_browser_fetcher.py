"""Tier 2 (Playwright) tests against a local file:// fixture — no network
access, no server, so this runs the same offline as everything else while
still exercising the real Playwright/Chromium integration.
"""

import os

import pytest

from lighthouse.scrapers.browser_fetcher import BrowserFetcher
from lighthouse.scrapers.config import FetcherConfig
from lighthouse.scrapers.website_fetcher import FetchStatus

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "html", "homepage_us_full.html"
)
FIXTURE_URL = "file://" + os.path.abspath(FIXTURE_PATH)


def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return os.path.exists("/opt/pw-browsers/chromium") or bool(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    )


pytestmark = pytest.mark.skipif(
    not _playwright_available(), reason="Playwright/Chromium not available"
)


def test_disabled_by_default_raises_on_construction() -> None:
    config = FetcherConfig(enable_playwright_fallback=False)
    with pytest.raises(RuntimeError):
        BrowserFetcher(config)


def test_fetch_rejects_file_url_via_the_same_ssrf_guard_as_tier_1() -> None:
    """file:// has no resolvable host, so the shared ssrf_guard correctly
    refuses it even with the scheme explicitly allow-listed — Tier 2 must
    never be a way to route around the guard Tier 1 enforces.
    """
    config = FetcherConfig(
        enable_playwright_fallback=True, allowed_schemes=("http", "https", "file")
    )
    with BrowserFetcher(config) as browser:
        result = browser.fetch(FIXTURE_URL)
    assert result.status == FetchStatus.SSRF_BLOCKED


def test_chromium_launches_and_renders_real_content_from_local_fixture() -> None:
    """Bypasses our own SSRF-guarded `fetch()` wrapper to directly prove
    the Playwright/Chromium integration itself (launch, navigate, read
    content, close) works end to end — using a local file so it needs no
    network and no server.
    """
    from playwright.sync_api import sync_playwright

    config = FetcherConfig(enable_playwright_fallback=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=config.playwright_executable_path, headless=True
        )
        try:
            page = browser.new_page()
            page.goto(FIXTURE_URL, timeout=config.playwright_timeout_ms)
            html = page.content()
            title = page.title()
        finally:
            browser.close()

    assert "Austin's Trusted Roofing Company" in html
    assert "Acme Roofing" in title
