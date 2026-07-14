"""Tier 1 (httpx) and Tier 2 (Playwright fallback) website fetchers.

This is the only module in Lighthouse that opens a socket. Everything
about *what* to do with a fetched page lives elsewhere (crawl.py picks
which URLs to fetch next, signal_extractor.py reads the result). This
module's only job is: given a URL, safely and deterministically produce a
FetchResult, or fail in a classified, auditable way.

Design notes:
- Redirects are followed manually (not via httpx's built-in
  follow_redirects) so every hop can be re-validated by ssrf_guard before
  we connect to it. A redirect to an internal IP is exactly the classic
  SSRF bypass this guards against.
- Retries only happen for transient failure classes (timeouts, network
  errors). Anything else (4xx, robots-blocked, oversized, wrong
  content-type, SSRF-blocked) is a stable outcome and retrying it would
  just be noise.
- `sleep_fn`/`jitter_fn` are injectable so retry/backoff behavior is
  unit-testable without a real clock or real randomness.
"""

from __future__ import annotations

import hashlib
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional
from urllib.parse import urljoin, urlsplit

import httpx

from lighthouse.scrapers.config import FetcherConfig
from lighthouse.scrapers.robots import RobotsCache
from lighthouse.scrapers.ssrf_guard import (
    DNSResolutionError,
    SSRFBlockedError,
    assert_url_is_safe,
)


class FetchStatus(str, Enum):
    SUCCESS = "success"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    DNS_ERROR = "dns_error"
    SSRF_BLOCKED = "ssrf_blocked"
    ROBOTS_BLOCKED = "robots_blocked"
    TOO_LARGE = "too_large"
    INVALID_CONTENT_TYPE = "invalid_content_type"
    TOO_MANY_REDIRECTS = "too_many_redirects"
    NETWORK_ERROR = "network_error"
    POLICY_BLOCKED = "policy_blocked"  # e.g. this sandbox's egress policy
    UNKNOWN_ERROR = "unknown_error"


TRANSIENT_STATUSES = {FetchStatus.TIMEOUT, FetchStatus.NETWORK_ERROR}


@dataclass
class FetchResult:
    requested_url: str
    final_url: Optional[str]
    status: FetchStatus
    http_status: Optional[int] = None
    headers: dict[str, str] = field(default_factory=dict)
    text: Optional[str] = None
    raw_bytes: Optional[bytes] = None
    content_hash: Optional[str] = None
    fetched_at: str = ""
    method: str = "http"
    attempts: int = 1
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == FetchStatus.SUCCESS


class ResponseTooLargeError(Exception):
    pass


class RateLimiter:
    """Serializes requests per-domain to at least `min_interval_s` apart.
    Thread-safe via a reserve-then-sleep pattern so concurrent workers
    hitting the same domain queue up correctly instead of racing.
    """

    def __init__(self, min_interval_s: float):
        self._min_interval = min_interval_s
        self._next_free: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, domain: str, sleep_fn: Callable[[float], None] = time.sleep) -> None:
        with self._lock:
            now = time.monotonic()
            earliest = self._next_free.get(domain, now)
            start_at = max(now, earliest)
            self._next_free[domain] = start_at + self._min_interval
        delay = max(0.0, start_at - now)
        sleep_fn(delay)


def classify_exception(exc: Exception) -> FetchStatus:
    """The single source of truth mapping an exception -> FetchStatus.
    Order matters: check subclasses before their parents.
    """
    if isinstance(exc, DNSResolutionError):
        return FetchStatus.DNS_ERROR
    if isinstance(exc, SSRFBlockedError):
        return FetchStatus.SSRF_BLOCKED
    if isinstance(exc, ResponseTooLargeError):
        return FetchStatus.TOO_LARGE
    if isinstance(exc, httpx.TooManyRedirects):
        return FetchStatus.TOO_MANY_REDIRECTS
    if isinstance(exc, httpx.ProxyError):
        # The environment's own egress proxy refused the CONNECT tunnel —
        # a permanent policy decision, not a transient network hiccup.
        # Must NOT be retried (see docs/lighthouse/Decision_Log.md).
        return FetchStatus.POLICY_BLOCKED
    if isinstance(
        exc,
        (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ),
    ):
        return FetchStatus.TIMEOUT
    if isinstance(
        exc, (httpx.ConnectError, httpx.NetworkError, httpx.RemoteProtocolError)
    ):
        return FetchStatus.NETWORK_ERROR
    if isinstance(exc, httpx.HTTPError):
        return FetchStatus.NETWORK_ERROR
    return FetchStatus.UNKNOWN_ERROR


def _content_type_allowed(headers: httpx.Headers, allowed: tuple[str, ...]) -> bool:
    ctype = headers.get("content-type", "")
    main_type = ctype.split(";")[0].strip().lower()
    if not main_type:
        return True  # some servers omit it; don't punish that alone
    return main_type in allowed


class WebsiteFetcher:
    """Tier 1: a real HTTP client with SSRF guarding, manual redirect
    revalidation, streamed size limiting, robots.txt enforcement, per-domain
    rate limiting, and bounded retries with backoff+jitter.
    """

    def __init__(
        self,
        config: FetcherConfig,
        rate_limiter: Optional[RateLimiter] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        jitter_fn: Callable[[float, float], float] = random.uniform,
    ):
        self.config = config
        self.rate_limiter = rate_limiter or RateLimiter(
            config.per_domain_min_interval_s
        )
        self._sleep_fn = sleep_fn
        self._jitter_fn = jitter_fn
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                connect=config.connect_timeout_s,
                read=config.read_timeout_s,
                write=config.read_timeout_s,
                pool=config.total_timeout_s,
            ),
            follow_redirects=False,
            headers={
                "User-Agent": config.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        self._robots = RobotsCache(fetch_text=self._fetch_robots_text)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "WebsiteFetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _fetch_robots_text(self, robots_url: str) -> str:
        # robots.txt is conventionally served as text/plain (not
        # text/html), so it must bypass the page content-type allowlist —
        # otherwise every real robots.txt fetch would be rejected and
        # robots.txt enforcement would silently become a no-op.
        result = self._fetch_once(
            robots_url, respect_robots=False, enforce_content_type=False
        )
        if not result.ok or result.text is None:
            raise RuntimeError(f"robots.txt fetch failed: {result.status}")
        return result.text

    def fetch(self, url: str) -> FetchResult:
        """Public entry point: fetch one URL with retries."""
        last_result: Optional[FetchResult] = None
        for attempt in range(1, self.config.retry_max_attempts + 1):
            result = self._fetch_once(
                url, respect_robots=self.config.respect_robots_txt
            )
            result.attempts = attempt
            if (
                result.status not in TRANSIENT_STATUSES
                or attempt == self.config.retry_max_attempts
            ):
                return result
            last_result = result
            delay = min(
                self.config.retry_max_delay_s,
                self.config.retry_base_delay_s * (2 ** (attempt - 1)),
            )
            delay *= self._jitter_fn(0.5, 1.5)
            self._sleep_fn(delay)
        assert last_result is not None, "retry_max_attempts must be >= 1"
        return last_result

    def _fetch_once(
        self, url: str, respect_robots: bool, enforce_content_type: bool = True
    ) -> FetchResult:
        now = datetime.now(timezone.utc).isoformat()
        current_url = url

        for hop in range(self.config.max_redirects + 1):
            try:
                assert_url_is_safe(current_url, self.config.allowed_schemes)
            except SSRFBlockedError as exc:
                return FetchResult(
                    requested_url=url,
                    final_url=current_url,
                    status=classify_exception(exc),
                    fetched_at=now,
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                )

            if respect_robots and self.config.respect_robots_txt:
                policy = self._robots.get_policy(current_url)
                if not policy.is_allowed(current_url, self.config.user_agent):
                    return FetchResult(
                        requested_url=url,
                        final_url=current_url,
                        status=FetchStatus.ROBOTS_BLOCKED,
                        fetched_at=now,
                        error_message="disallowed by robots.txt",
                    )

            domain = urlsplit(current_url).netloc
            self.rate_limiter.wait(domain, sleep_fn=self._sleep_fn)

            try:
                body, response = self._stream_get(current_url)
            except Exception as exc:  # classified below, not swallowed
                return FetchResult(
                    requested_url=url,
                    final_url=current_url,
                    status=classify_exception(exc),
                    fetched_at=now,
                    error_code=type(exc).__name__,
                    error_message=str(exc),
                )

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    return FetchResult(
                        requested_url=url,
                        final_url=current_url,
                        status=FetchStatus.NETWORK_ERROR,
                        fetched_at=now,
                        error_message="redirect with no Location header",
                    )
                current_url = urljoin(current_url, location)
                continue

            if enforce_content_type and not _content_type_allowed(
                response.headers, self.config.allowed_content_types
            ):
                return FetchResult(
                    requested_url=url,
                    final_url=current_url,
                    status=FetchStatus.INVALID_CONTENT_TYPE,
                    http_status=response.status_code,
                    headers=dict(response.headers),
                    fetched_at=now,
                )

            text = body.decode(response.encoding or "utf-8", errors="replace")
            content_hash = hashlib.sha256(body).hexdigest()
            status = (
                FetchStatus.SUCCESS
                if 200 <= response.status_code < 300
                else FetchStatus.HTTP_ERROR
            )

            return FetchResult(
                requested_url=url,
                final_url=current_url,
                status=status,
                http_status=response.status_code,
                headers=dict(response.headers),
                text=text,
                raw_bytes=body,
                content_hash=content_hash,
                fetched_at=now,
            )

        return FetchResult(
            requested_url=url,
            final_url=current_url,
            status=FetchStatus.TOO_MANY_REDIRECTS,
            fetched_at=now,
            error_message=f"exceeded {self.config.max_redirects} redirects",
        )

    def _stream_get(self, url: str) -> tuple[bytes, httpx.Response]:
        with self._client.stream("GET", url) as response:
            chunks: list[bytes] = []
            total = 0
            cap = self.config.max_response_bytes
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > cap:
                    raise ResponseTooLargeError(f"{url} exceeded {cap} bytes")
                chunks.append(chunk)
            return b"".join(chunks), response
