"""Controlled, same-domain link discovery.

Given a homepage's HTML, find candidate URLs worth crawling next. This is
deliberately not a general-purpose crawler: it never leaves the company's
own domain, never goes past the configured page/depth caps, and only
follows links whose URL or anchor text matches the brief's fixed keyword
list (projects, portfolio, testimonials, about, warranty, ...).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

from lighthouse.scrapers.config import CRAWL_PRIORITY_KEYWORDS

_LINK_RE = re.compile(
    r'<a\b[^>]*\bhref\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")

# Tracking params that should never affect de-duplication.
_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


@dataclass(frozen=True)
class CrawlCandidate:
    url: str
    anchor_text: str
    priority: int  # higher = more relevant


def canonicalize_url(url: str) -> str:
    """Strip fragment + tracking params, lowercase scheme/host, drop a
    trailing slash (except for the bare root), so link variants that
    point at the same page dedupe cleanly.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS
    ]
    query = urlencode(sorted(query_pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


def _same_domain(url: str, base_domain: str) -> bool:
    host = urlsplit(url).netloc.lower()
    base_domain = base_domain.lower()
    return (
        host == base_domain
        or host == f"www.{base_domain}"
        or f"www.{host}" == base_domain
    )


def _priority_of(url: str, anchor_text: str) -> int:
    haystack = f"{url} {anchor_text}".lower()
    return sum(1 for kw in CRAWL_PRIORITY_KEYWORDS if kw in haystack)


def discover_links(base_url: str, html: str, max_pages: int) -> list[CrawlCandidate]:
    """Return up to `max_pages` same-domain CrawlCandidates, ranked by
    keyword relevance (ties broken by first-seen order for determinism).
    """
    base_domain = urlsplit(base_url).netloc
    seen = set()
    candidates = []

    for match in _LINK_RE.finditer(html):
        href, inner_html = match.group(1), match.group(2)
        anchor_text = _TAG_RE.sub(" ", inner_html).strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if not absolute.startswith(("http://", "https://")):
            continue
        canonical = canonicalize_url(absolute)
        if canonical == canonicalize_url(base_url):
            continue
        if not _same_domain(canonical, base_domain):
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        priority = _priority_of(canonical, anchor_text)
        if priority > 0:
            candidates.append(
                CrawlCandidate(
                    url=canonical, anchor_text=anchor_text, priority=priority
                )
            )

    candidates.sort(key=lambda c: c.priority, reverse=True)
    return candidates[:max_pages]
