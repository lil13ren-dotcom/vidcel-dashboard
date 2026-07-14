"""SSRF and private-network protections for the acquisition layer.

Every outbound fetch (homepage, crawled page, robots.txt) must pass through
`assert_url_is_safe` before a socket is opened, and `assert_ip_is_safe` must
be re-checked against the IP actually dialed on every redirect hop — a
redirect can point somewhere new, so validating the original URL once is
not sufficient.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit


class SSRFBlockedError(Exception):
    """Raised when a URL or resolved IP fails the safety check."""


class DNSResolutionError(SSRFBlockedError):
    """Raised specifically for DNS resolution failures, so callers can
    distinguish "couldn't resolve the name" (transient/network-ish) from
    "resolved, but to a blocked address" (a real policy block) without
    string-matching exception messages.
    """


@dataclass(frozen=True)
class ResolvedTarget:
    hostname: str
    port: int
    ip: str


_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),  # loopback
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),  # benchmarking
    ipaddress.ip_network("224.0.0.0/4"),  # multicast
    ipaddress.ip_network("240.0.0.0/4"),  # reserved
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),  # unique local
    ipaddress.ip_network("fe80::/10"),  # link-local v6
]


def assert_scheme_is_safe(url: str, allowed_schemes: tuple[str, ...]) -> None:
    scheme = urlsplit(url).scheme.lower()
    if scheme not in allowed_schemes:
        raise SSRFBlockedError(
            f"scheme {scheme!r} not in allowed schemes {allowed_schemes!r}"
        )


def is_ip_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable -> treat as unsafe
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True
    return any(ip in net for net in _BLOCKED_NETWORKS)


def resolve_and_validate(hostname: str, port: int) -> ResolvedTarget:
    """DNS-resolve a hostname and reject it if any resolved address is
    private/loopback/link-local/reserved (DNS rebinding protection: we
    validate the specific address the connection will use, not just the
    hostname string).
    """
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise DNSResolutionError(
            f"DNS resolution failed for {hostname}: {exc}"
        ) from exc

    if not infos:
        raise SSRFBlockedError(f"DNS resolution returned no addresses for {hostname}")

    first_ip: Optional[str] = None
    for _family, _type, _proto, _canon, sockaddr in infos:
        ip_str = str(sockaddr[0])
        if first_ip is None:
            first_ip = ip_str
        if is_ip_blocked(ip_str):
            raise SSRFBlockedError(
                f"{hostname} resolves to a blocked address ({ip_str})"
            )

    assert first_ip is not None, "infos was non-empty but no IP was extracted"
    return ResolvedTarget(hostname=hostname, port=port, ip=first_ip)


def assert_url_is_safe(url: str, allowed_schemes: tuple[str, ...]) -> ResolvedTarget:
    """Full pre-flight check for a URL: scheme + DNS + IP range. Call this
    before the initial request AND again for the Location of every redirect
    hop, since the safe-scheme/safe-host check on the original URL says
    nothing about where a redirect leads.
    """
    assert_scheme_is_safe(url, allowed_schemes)
    parts = urlsplit(url)
    hostname = parts.hostname
    if not hostname:
        raise SSRFBlockedError(f"URL has no hostname: {url}")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return resolve_and_validate(hostname, port)
