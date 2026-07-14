import socket
from typing import Any

import httpx
import pytest
import respx

from lighthouse.scrapers.config import FetcherConfig
from lighthouse.scrapers.website_fetcher import (
    FetchStatus,
    RateLimiter,
    WebsiteFetcher,
    classify_exception,
)
from lighthouse.scrapers.ssrf_guard import DNSResolutionError, SSRFBlockedError


@pytest.fixture(autouse=True)
def no_real_dns(monkeypatch) -> None:
    """Every test in this module must be network-independent, including
    DNS. Route any hostname to a fixed public IP so ssrf_guard's checks
    run deterministically without touching a real resolver.
    """

    def fake_getaddrinfo(host, port, proto=None) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def _fast_config(**overrides: Any) -> FetcherConfig:
    base: dict[str, Any] = dict(
        retry_max_attempts=3,
        retry_base_delay_s=0.01,
        retry_max_delay_s=0.02,
        per_domain_min_interval_s=0.0,
        respect_robots_txt=False,
        max_response_bytes=1_000_000,
    )
    base.update(overrides)
    return FetcherConfig(**base)


def _fetcher(config, sleep_fn=lambda s: None) -> WebsiteFetcher:
    return WebsiteFetcher(config, sleep_fn=sleep_fn, jitter_fn=lambda a, b: 1.0)


# --- error classification ---------------------------------------------


def test_classify_exception_maps_ssrf_and_dns_errors() -> None:
    assert classify_exception(SSRFBlockedError("x")) == FetchStatus.SSRF_BLOCKED
    assert classify_exception(DNSResolutionError("x")) == FetchStatus.DNS_ERROR


def test_classify_exception_maps_proxy_error_to_policy_blocked_not_retryable() -> None:
    from lighthouse.scrapers.website_fetcher import TRANSIENT_STATUSES

    status = classify_exception(httpx.ProxyError("403 Forbidden"))
    assert status == FetchStatus.POLICY_BLOCKED
    assert status not in TRANSIENT_STATUSES


def test_classify_exception_maps_timeouts() -> None:
    assert classify_exception(httpx.ConnectTimeout("t")) == FetchStatus.TIMEOUT
    assert classify_exception(httpx.ReadTimeout("t")) == FetchStatus.TIMEOUT


def test_classify_exception_maps_too_many_redirects() -> None:
    assert (
        classify_exception(httpx.TooManyRedirects("r"))
        == FetchStatus.TOO_MANY_REDIRECTS
    )


def test_classify_exception_unknown_falls_back() -> None:
    assert classify_exception(ValueError("weird")) == FetchStatus.UNKNOWN_ERROR


# --- successful fetch, redirects, content-type, size caps --------------


@respx.mock
def test_successful_fetch_returns_success_with_text_and_hash() -> None:
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(
            200, html="<html>hi</html>", headers={"content-type": "text/html"}
        )
    )
    with _fetcher(_fast_config()) as fetcher:
        result = fetcher.fetch("https://example.com/")
    assert result.status == FetchStatus.SUCCESS
    assert result.http_status == 200
    assert result.text is not None and "hi" in result.text
    assert result.content_hash is not None


@respx.mock
def test_redirect_is_followed_and_final_url_updated() -> None:
    respx.get("https://example.com/old").mock(
        return_value=httpx.Response(
            301, headers={"location": "https://example.com/new"}
        )
    )
    respx.get("https://example.com/new").mock(
        return_value=httpx.Response(
            200, html="<html>new</html>", headers={"content-type": "text/html"}
        )
    )
    with _fetcher(_fast_config()) as fetcher:
        result = fetcher.fetch("https://example.com/old")
    assert result.status == FetchStatus.SUCCESS
    assert result.final_url == "https://example.com/new"


@respx.mock
def test_redirect_hop_is_revalidated_against_ssrf_guard(monkeypatch) -> None:
    """A redirect to a private IP must be blocked even though the
    original URL was public — this is the classic SSRF-via-redirect bypass.
    """
    respx.get("https://example.com/redirect-to-internal").mock(
        return_value=httpx.Response(
            302, headers={"location": "https://internal.example/secret"}
        )
    )

    def selective_dns(host, port, proto=None) -> list:
        if host == "internal.example":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", selective_dns)

    with _fetcher(_fast_config()) as fetcher:
        result = fetcher.fetch("https://example.com/redirect-to-internal")
    assert result.status == FetchStatus.SSRF_BLOCKED


@respx.mock
def test_too_many_redirects_is_classified() -> None:
    for i in range(10):
        respx.get(f"https://example.com/hop{i}").mock(
            return_value=httpx.Response(
                302, headers={"location": f"https://example.com/hop{i + 1}"}
            )
        )
    with _fetcher(_fast_config(max_redirects=3)) as fetcher:
        result = fetcher.fetch("https://example.com/hop0")
    assert result.status == FetchStatus.TOO_MANY_REDIRECTS


@respx.mock
def test_invalid_content_type_is_rejected() -> None:
    respx.get("https://example.com/file.pdf").mock(
        return_value=httpx.Response(
            200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"}
        )
    )
    with _fetcher(_fast_config()) as fetcher:
        result = fetcher.fetch("https://example.com/file.pdf")
    assert result.status == FetchStatus.INVALID_CONTENT_TYPE


@respx.mock
def test_oversized_response_is_rejected() -> None:
    big_html = "<html>" + ("x" * 5000) + "</html>"
    respx.get("https://example.com/big").mock(
        return_value=httpx.Response(
            200, html=big_html, headers={"content-type": "text/html"}
        )
    )
    with _fetcher(_fast_config(max_response_bytes=100)) as fetcher:
        result = fetcher.fetch("https://example.com/big")
    assert result.status == FetchStatus.TOO_LARGE


@respx.mock
def test_http_error_status_is_classified_but_not_absent() -> None:
    respx.get("https://example.com/missing").mock(
        return_value=httpx.Response(
            404, html="<html>not found</html>", headers={"content-type": "text/html"}
        )
    )
    with _fetcher(_fast_config()) as fetcher:
        result = fetcher.fetch("https://example.com/missing")
    assert result.status == FetchStatus.HTTP_ERROR
    assert result.http_status == 404


# --- retry / backoff behavior -------------------------------------------


@respx.mock
def test_transient_timeout_is_retried_and_can_succeed() -> None:
    route = respx.get("https://example.com/flaky")
    route.side_effect = [
        httpx.ConnectTimeout("boom"),
        httpx.Response(
            200, html="<html>ok</html>", headers={"content-type": "text/html"}
        ),
    ]
    with _fetcher(_fast_config(retry_max_attempts=3)) as fetcher:
        result = fetcher.fetch("https://example.com/flaky")
    assert result.status == FetchStatus.SUCCESS
    assert result.attempts == 2


@respx.mock
def test_timeout_exhausts_retries_and_reports_timeout() -> None:
    respx.get("https://example.com/always-times-out").mock(
        side_effect=httpx.ConnectTimeout("boom")
    )
    with _fetcher(_fast_config(retry_max_attempts=3)) as fetcher:
        result = fetcher.fetch("https://example.com/always-times-out")
    assert result.status == FetchStatus.TIMEOUT
    assert result.attempts == 3


@respx.mock
def test_policy_block_is_not_retried() -> None:
    route = respx.get("https://example.com/blocked")
    route.side_effect = [
        httpx.ProxyError("403 Forbidden"),
        httpx.Response(200, html="<html>should not reach</html>"),
    ]
    with _fetcher(_fast_config(retry_max_attempts=3)) as fetcher:
        result = fetcher.fetch("https://example.com/blocked")
    assert result.status == FetchStatus.POLICY_BLOCKED
    assert result.attempts == 1  # must not have retried into the second mocked response


@respx.mock
def test_http_error_is_not_retried() -> None:
    route = respx.get("https://example.com/notfound")
    route.side_effect = [
        httpx.Response(404),
        httpx.Response(200, html="<html>should not reach</html>"),
    ]
    with _fetcher(_fast_config(retry_max_attempts=3)) as fetcher:
        result = fetcher.fetch("https://example.com/notfound")
    assert result.status == FetchStatus.HTTP_ERROR
    assert result.attempts == 1


# --- robots.txt handling -------------------------------------------------


@respx.mock
def test_robots_disallow_blocks_fetch() -> None:
    respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
    )
    respx.get("https://example.com/private/data").mock(
        return_value=httpx.Response(200, html="<html>secret</html>")
    )
    with _fetcher(_fast_config(respect_robots_txt=True)) as fetcher:
        result = fetcher.fetch("https://example.com/private/data")
    assert result.status == FetchStatus.ROBOTS_BLOCKED


@respx.mock
def test_robots_allows_unlisted_paths() -> None:
    respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
    )
    respx.get("https://example.com/public").mock(
        return_value=httpx.Response(
            200, html="<html>ok</html>", headers={"content-type": "text/html"}
        )
    )
    with _fetcher(_fast_config(respect_robots_txt=True)) as fetcher:
        result = fetcher.fetch("https://example.com/public")
    assert result.status == FetchStatus.SUCCESS


@respx.mock
def test_missing_robots_txt_defaults_to_allow() -> None:
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://example.com/page").mock(
        return_value=httpx.Response(
            200, html="<html>ok</html>", headers={"content-type": "text/html"}
        )
    )
    with _fetcher(_fast_config(respect_robots_txt=True)) as fetcher:
        result = fetcher.fetch("https://example.com/page")
    assert result.status == FetchStatus.SUCCESS


# --- rate limiter ---------------------------------------------------------


def test_rate_limiter_serializes_same_domain_requests() -> None:
    calls = []
    limiter = RateLimiter(min_interval_s=5.0)
    limiter.wait("example.com", sleep_fn=lambda s: calls.append(s))
    limiter.wait("example.com", sleep_fn=lambda s: calls.append(s))
    assert calls[0] == 0  # first call: nothing to wait for
    assert calls[1] > 0  # second call to same domain: must wait
