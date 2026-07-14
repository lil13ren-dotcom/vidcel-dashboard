"""Tier 2: Playwright fallback for JS-dependent pages.

Only invoked when the caller (acquisition_pipeline.py) has already run the
URL through Tier 1 (WebsiteFetcher) and either:
  - got a SUCCESS with HTML that looks JS-dependent (near-empty <body>,
    a client-side-rendering root div and no server-rendered content), or
  - hit a supported interstitial condition.

Known limitation (documented, not silently ignored): this module performs
one SSRF pre-check on the *initial* URL only. A real browser follows
redirects internally and we cannot re-validate each hop the way Tier 1
does, so Tier 2 must only ever be pointed at a domain Tier 1 has already
fetched successfully — never used as the first touch of an unknown URL.

Disabled unless FetcherConfig.enable_playwright_fallback=True. No login,
no CAPTCHA solving, no stealth/evasion — just load the page and read what
a normal visitor would see.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from lighthouse.scrapers.config import FetcherConfig
from lighthouse.scrapers.ssrf_guard import SSRFBlockedError, assert_url_is_safe
from lighthouse.scrapers.website_fetcher import (
    FetchResult,
    FetchStatus,
    classify_exception,
)

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Playwright


@dataclass
class RenderedPage:
    url: str
    final_url: str
    html: str
    screenshot_png: Optional[bytes]


class BrowserFetcher:
    """Thin wrapper around Playwright's sync API. Constructed lazily so
    importing this module never requires Playwright to be installed unless
    the fallback is actually enabled and used.
    """

    def __init__(self, config: FetcherConfig):
        if not config.enable_playwright_fallback:
            raise RuntimeError(
                "BrowserFetcher constructed while enable_playwright_fallback=False"
            )
        self.config = config
        self._playwright: Optional["Playwright"] = None
        self._browser: Optional["Browser"] = None

    def __enter__(self) -> "BrowserFetcher":
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            executable_path=self.config.playwright_executable_path,
            headless=True,
        )
        return self

    def __exit__(self, *exc: object) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def fetch(self, url: str) -> FetchResult:
        now = datetime.now(timezone.utc).isoformat()
        try:
            assert_url_is_safe(url, self.config.allowed_schemes)
        except SSRFBlockedError as exc:
            return FetchResult(
                requested_url=url,
                final_url=url,
                status=classify_exception(exc),
                fetched_at=now,
                method="playwright",
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

        assert self._browser is not None, (
            "BrowserFetcher must be used as a context manager"
        )
        page = self._browser.new_page(user_agent=self.config.user_agent)
        # Block heavy media we don't need for text/structure extraction.
        page.route(
            "**/*",
            lambda route: (
                route.abort()
                if route.request.resource_type in ("media", "font")
                else route.continue_()
            ),
        )
        try:
            response = page.goto(
                url,
                timeout=self.config.playwright_timeout_ms,
                wait_until="networkidle",
            )
            html = page.content()
            screenshot = (
                page.screenshot(full_page=True)
                if self.config.playwright_capture_screenshot
                else None
            )
            status_code = response.status if response else None
            fetch_status = (
                FetchStatus.SUCCESS
                if status_code and 200 <= status_code < 300
                else FetchStatus.HTTP_ERROR
            )
            return FetchResult(
                requested_url=url,
                final_url=page.url,
                status=fetch_status,
                http_status=status_code,
                text=html,
                content_hash=None,
                fetched_at=now,
                method="playwright",
                raw_bytes=screenshot,
            )
        except Exception as exc:  # Playwright raises its own TimeoutError etc.
            return FetchResult(
                requested_url=url,
                final_url=url,
                status=FetchStatus.NETWORK_ERROR,
                fetched_at=now,
                method="playwright",
                error_code=type(exc).__name__,
                error_message=str(exc),
            )
        finally:
            page.close()
