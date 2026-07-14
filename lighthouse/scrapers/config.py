"""Tunables for the acquisition layer. One object, passed explicitly —
no hidden globals, so tests can construct a strict/fast config and
production code can use conservative defaults.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FetcherConfig:
    user_agent: str = (
        "LighthouseResearchBot/1.1 (+https://vidcel.example/lighthouse-bot; "
        "market-research acquisition; contact: research@vidcel.example)"
    )
    connect_timeout_s: float = 5.0
    read_timeout_s: float = 10.0
    total_timeout_s: float = 15.0
    max_redirects: int = 5
    max_response_bytes: int = 5_000_000  # 5 MB per page
    max_bytes_per_company: int = 20_000_000  # 20 MB across all pages for one company
    allowed_content_types: tuple[str, ...] = ("text/html", "application/xhtml+xml")
    allowed_schemes: tuple[str, ...] = ("http", "https")
    retry_max_attempts: int = 3
    retry_base_delay_s: float = 0.5
    retry_max_delay_s: float = 8.0
    per_domain_min_interval_s: float = 1.0
    global_concurrency: int = 4
    respect_robots_txt: bool = True

    # Crawl scope
    max_pages_per_company: int = 5
    max_crawl_depth: int = 1  # homepage (depth 0) + up to 1 hop to discovered pages

    # Tier 2 (Playwright) — off unless a caller explicitly opts in.
    enable_playwright_fallback: bool = False
    playwright_timeout_ms: int = 15_000
    playwright_executable_path: str = "/opt/pw-browsers/chromium"
    playwright_capture_screenshot: bool = False

    collector_version: str = "lighthouse-fetcher-1.1.0"


DEFAULT_CONFIG = FetcherConfig()

# Keywords used to prioritize which discovered links get crawled, per the
# brief's controlled scope (never a site-wide crawl).
CRAWL_PRIORITY_KEYWORDS = [
    "project",
    "portfolio",
    "gallery",
    "work",
    "case-stud",
    "case_stud",
    "before",
    "after",
    "testimonial",
    "review",
    "about",
    "team",
    "staff",
    "warranty",
    "financ",
    "contact",
    "estimate",
    "quote",
    "career",
    "service-area",
    "service_area",
    "areas-we-serve",
    "faq",
]
