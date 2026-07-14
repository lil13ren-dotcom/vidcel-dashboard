import socket

import pytest

from lighthouse.scrapers.ssrf_guard import (
    DNSResolutionError,
    SSRFBlockedError,
    assert_scheme_is_safe,
    assert_url_is_safe,
    is_ip_blocked,
    resolve_and_validate,
)


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.1.1",
        "0.0.0.0",
        "::1",
        "fe80::1",
        "fc00::1",
        "100.64.0.1",
    ],
)
def test_private_and_reserved_ips_are_blocked(ip) -> None:
    assert is_ip_blocked(ip) is True


@pytest.mark.parametrize("ip", ["93.184.216.34", "8.8.8.8", "1.1.1.1"])
def test_public_ips_are_not_blocked(ip) -> None:
    assert is_ip_blocked(ip) is False


def test_unparseable_ip_is_treated_as_blocked() -> None:
    assert is_ip_blocked("not-an-ip") is True


def test_scheme_check_rejects_non_http_schemes() -> None:
    with pytest.raises(SSRFBlockedError):
        assert_scheme_is_safe("ftp://example.com/file", ("http", "https"))
    with pytest.raises(SSRFBlockedError):
        assert_scheme_is_safe("file:///etc/passwd", ("http", "https"))


def test_scheme_check_allows_http_and_https() -> None:
    assert_scheme_is_safe("https://example.com", ("http", "https"))
    assert_scheme_is_safe("http://example.com", ("http", "https"))


def test_resolve_and_validate_blocks_loopback(monkeypatch) -> None:
    def fake_getaddrinfo(host, port, proto=None) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SSRFBlockedError):
        resolve_and_validate("internal.example", 443)


def test_resolve_and_validate_allows_public_ip(monkeypatch) -> None:
    def fake_getaddrinfo(host, port, proto=None) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    target = resolve_and_validate("example.com", 443)
    assert target.ip == "93.184.216.34"


def test_dns_failure_raises_specific_subclass(monkeypatch) -> None:
    def fake_getaddrinfo(host, port, proto=None) -> list:
        raise socket.gaierror("name not known")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(DNSResolutionError):
        resolve_and_validate("nonexistent.invalid", 443)


def test_assert_url_is_safe_rejects_dns_rebinding_to_private_ip(monkeypatch) -> None:
    """A hostname that looks fine but resolves to a private IP must be
    blocked at resolution time, not accepted because the URL string looks
    like a normal public domain.
    """

    def fake_getaddrinfo(host, port, proto=None) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SSRFBlockedError):
        assert_url_is_safe("https://looks-legit.example/metadata", ("http", "https"))
