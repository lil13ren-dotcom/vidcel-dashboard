"""Deterministic, evidence-producing signal extraction from fetched pages.

This replaces Phase 1's LLM-based `prompts/website_signal_prompt.py` for
website-signal detection: once we have real fetched HTML, keyword/structure
heuristics over that HTML are more auditable and reproducible than asking
an LLM to describe a page (same input always yields the same output, and
every conclusion carries the exact snippet that produced it). The LLM
prompt file is kept for historical reference (see Decision_Log.md) and
because Phase 1's method — reconstructing signals from search snippets —
is a fundamentally different (and inferior) evidence source, not because
LLMs can't parse HTML.

Every signal is graded on the same rule: a positive match anywhere in the
successfully-fetched pages -> PRESENT with the matching snippet as
evidence. No match, but we successfully fetched a page targeted at that
signal's topic (or the homepage, for site-wide signals) -> ABSENT. No
matching page was ever successfully fetched -> UNKNOWN (we simply don't
have enough scope to conclude absence).
"""

from __future__ import annotations

import re
from typing import Callable, Optional
from urllib.parse import urlsplit

from lighthouse.models import (
    Evidence,
    EvidenceSignals,
    EvidenceStatus,
    WEBSITE_SIGNAL_KEYS,
)
from lighthouse.scrapers.website_fetcher import FetchResult, FetchStatus

# Which crawled-page keyword category (see config.CRAWL_PRIORITY_KEYWORDS)
# counts as "sufficient scope" to call a signal ABSENT when no match is
# found. Empty list = judged site-wide, so the homepage alone is enough.
_SIGNAL_SCOPE_KEYWORDS = {
    "https": [],
    "mobile_friendly": [],
    "cta": [],
    "quote_form": ["quote", "estimate", "contact"],
    "contact_form": ["contact"],
    "financing": ["financ"],
    "warranty": ["warranty"],
    "faq": ["faq"],
    "about_us": ["about"],
    "team_page": ["team", "staff", "about"],
    "certifications": [],
    "service_area": ["service-area", "service_area", "areas-we-serve", "about"],
    "portfolio": ["project", "portfolio", "gallery", "work"],
    "case_studies": ["case-stud", "case_stud", "project"],
    "before_after": ["before", "after", "project", "portfolio", "gallery"],
    "testimonials": ["testimonial", "review"],
    "customer_photos": ["testimonial", "review", "project", "portfolio", "gallery"],
    "customer_videos": ["testimonial", "review", "about"],
}

_CTA_PHRASES = [
    "get a quote",
    "get your quote",
    "free quote",
    "call now",
    "schedule service",
    "book now",
    "free estimate",
    "request a quote",
    "request an estimate",
    "schedule an estimate",
    "contact us today",
    "get started",
]
_FINANCING_WORDS = [
    "financing",
    "payment plan",
    "0% apr",
    "monthly payments",
    "affirm",
    "synchrony",
]
_WARRANTY_WORDS = ["warranty", "guarantee", "guaranteed"]
_FAQ_WORDS = ["frequently asked questions", "faq"]
_ABOUT_WORDS = ["about us", "our story", "who we are"]
_TEAM_WORDS = ["meet the team", "meet our team", "our team", "our staff"]
_CERT_WORDS = [
    "certified",
    "licensed",
    "bbb accredited",
    "better business bureau",
    "association",
    "member of",
]
_SERVICE_AREA_WORDS = ["service area", "areas we serve", "we serve", "serving the"]
_PORTFOLIO_WORDS = [
    "our work",
    "portfolio",
    "gallery",
    "recent projects",
    "completed projects",
]
_CASE_STUDY_WORDS = ["case study", "case studies", "project spotlight"]
_TESTIMONIAL_WORDS = ["testimonial", "what our customers say", "customer reviews"]
_QUOTE_FORM_HINTS = [
    r"<form[^>]*>(?:(?!</form>).)*?(quote|estimate)",
]
_CONTACT_FORM_HINTS = [
    r"<form[^>]*>(?:(?!</form>).)*?(name.{0,40}email.{0,80}message|contact us)",
]
_VIEWPORT_RE = re.compile(
    r'<meta[^>]+name=["\']viewport["\'][^>]*content=["\'][^"\']*width=device-width',
    re.IGNORECASE,
)
# Statuses where we actually completed a TLS handshake and got real HTTP
# semantics back from the target host — as opposed to POLICY_BLOCKED,
# SSRF_BLOCKED, DNS_ERROR, TIMEOUT, NETWORK_ERROR, or ROBOTS_BLOCKED, none
# of which prove anything about how *this* page actually behaves over the
# wire. `https` must only be confirmed from one of these.
_RESPONSE_RECEIVED_STATUSES = {
    FetchStatus.SUCCESS,
    FetchStatus.HTTP_ERROR,
    FetchStatus.TOO_MANY_REDIRECTS,
    FetchStatus.TOO_LARGE,
    FetchStatus.INVALID_CONTENT_TYPE,
}

_BEFORE_AFTER_WORDS = ["before and after", "before & after", "before/after"]
_BEFORE_AFTER_IMG_RE = re.compile(
    r'(?:src|alt)=["\'][^"\']*before[-_ ]?after[^"\']*["\']', re.IGNORECASE
)

SOCIAL_URL_RE = {
    "instagram": re.compile(
        r"https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.\-/]+", re.IGNORECASE
    ),
    "facebook": re.compile(
        r"https?://(?:www\.)?facebook\.com/[a-zA-Z0-9_.\-/]+", re.IGNORECASE
    ),
    "youtube": re.compile(
        r"https?://(?:www\.)?youtube\.com/[a-zA-Z0-9_.\-/@]+", re.IGNORECASE
    ),
    "tiktok": re.compile(
        r"https?://(?:www\.)?tiktok\.com/[a-zA-Z0-9_.\-/@]+", re.IGNORECASE
    ),
}


def _find_any(text: str, phrases: list[str]) -> str:
    low = text.lower()
    for phrase in phrases:
        idx = low.find(phrase)
        if idx != -1:
            start = max(0, idx - 30)
            return text[start : idx + len(phrase) + 30].strip()
    return ""


def _page_matches_scope(url: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    low = url.lower()
    return any(kw in low for kw in keywords)


def _detect_cta(text: str) -> str:
    return _find_any(text, _CTA_PHRASES)


def _detect_quote_form(text: str) -> str:
    for pattern in _QUOTE_FORM_HINTS:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(0)[:120]
    return ""


def _detect_contact_form(text: str) -> str:
    if "<form" not in text.lower():
        return ""
    for pattern in _CONTACT_FORM_HINTS:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(0)[:120]
    return ""


def _detect_before_after(text: str) -> str:
    snippet = _find_any(text, _BEFORE_AFTER_WORDS)
    if snippet:
        return snippet
    m = _BEFORE_AFTER_IMG_RE.search(text)
    return m.group(0) if m else ""


_DETECTORS: dict[str, Callable[[str], str]] = {
    "cta": _detect_cta,
    "quote_form": _detect_quote_form,
    "contact_form": _detect_contact_form,
    "financing": lambda t: _find_any(t, _FINANCING_WORDS),
    "warranty": lambda t: _find_any(t, _WARRANTY_WORDS),
    "faq": lambda t: _find_any(t, _FAQ_WORDS),
    "about_us": lambda t: _find_any(t, _ABOUT_WORDS),
    "team_page": lambda t: _find_any(t, _TEAM_WORDS),
    "certifications": lambda t: _find_any(t, _CERT_WORDS),
    "service_area": lambda t: _find_any(t, _SERVICE_AREA_WORDS),
    "portfolio": lambda t: _find_any(t, _PORTFOLIO_WORDS),
    "case_studies": lambda t: _find_any(t, _CASE_STUDY_WORDS),
    "before_after": _detect_before_after,
    "testimonials": lambda t: _find_any(t, _TESTIMONIAL_WORDS),
}


def _successful_pages(pages: list[FetchResult]) -> list[FetchResult]:
    return [p for p in pages if p.status == FetchStatus.SUCCESS and p.text]


def _detect_https(
    pages: list[FetchResult], collected_at: str, collector_version: str
) -> Evidence:
    homepage = pages[0] if pages else None
    if homepage is None or homepage.final_url is None:
        return Evidence.unknown(
            "no response received; scheme could not be observed",
            collected_at,
            collector_version,
        )
    if homepage.status not in _RESPONSE_RECEIVED_STATUSES:
        return Evidence.unknown(
            f"fetch failed before a response was received ({homepage.status.value}); "
            "the requested URL's scheme is not evidence of what the site actually serves",
            collected_at,
            collector_version,
        )
    scheme = urlsplit(homepage.final_url).scheme.lower()
    if scheme == "https":
        return Evidence.present(
            homepage.final_url,
            f"final URL uses {scheme}://",
            collected_at,
            collector_version,
        )
    if scheme == "http":
        return Evidence.absent(
            homepage.final_url,
            collected_at,
            collector_version,
            evidence_text=f"final URL uses {scheme}://",
        )
    return Evidence.unknown(
        f"unexpected scheme {scheme!r}", collected_at, collector_version
    )


def _detect_mobile_friendly(
    pages: list[FetchResult], collected_at: str, collector_version: str
) -> Evidence:
    successful = _successful_pages(pages)
    if not successful:
        return Evidence.unknown(
            "homepage was not successfully fetched", collected_at, collector_version
        )
    homepage = successful[0]
    assert homepage.text is not None  # guaranteed by _successful_pages
    if _VIEWPORT_RE.search(homepage.text):
        return Evidence.present(
            homepage.final_url,
            "responsive viewport meta tag found",
            collected_at,
            collector_version,
        )
    return Evidence.absent(
        homepage.final_url,
        collected_at,
        collector_version,
        evidence_text="no responsive viewport meta tag found in fetched HTML",
    )


def _detect_customer_photos(
    pages: list[FetchResult], collected_at: str, collector_version: str
) -> Evidence:
    """Image-dependent signal — per the brief, never claim visual
    confirmation from text/structure alone. We surface a low-confidence
    'candidate' PRESENT only on strong textual evidence (explicit
    "customer photo" captions), and otherwise report UNKNOWN so a human
    or a future vision-review step makes the final call.
    """
    for page in _successful_pages(pages):
        assert page.text is not None  # guaranteed by _successful_pages
        snippet = _find_any(
            page.text, ["customer photo", "photo submitted by", "sent us this photo"]
        )
        if snippet:
            return Evidence(
                status=EvidenceStatus.PRESENT,
                value=True,
                confidence=0.4,
                source_url=page.final_url,
                evidence_text=f"candidate only, needs visual review: {snippet}",
                collected_at=collected_at,
                collector_version=collector_version,
            )
    return Evidence.unknown(
        "image-dependent signal; textual heuristics found no explicit caption and no visual/vision review was performed",
        collected_at,
        collector_version,
    )


def _detect_customer_videos(
    pages: list[FetchResult], collected_at: str, collector_version: str
) -> Evidence:
    video_re = re.compile(
        r"<video\b|youtube\.com/embed|player\.vimeo\.com", re.IGNORECASE
    )
    for page in _successful_pages(pages):
        assert page.text is not None  # guaranteed by _successful_pages
        m = video_re.search(page.text)
        if m:
            return Evidence.present(
                page.final_url,
                m.group(0),
                collected_at,
                collector_version,
                confidence=0.7,
            )
    if not _successful_pages(pages):
        return Evidence.unknown(
            "no pages successfully fetched", collected_at, collector_version
        )
    return Evidence.absent(
        pages[0].final_url,
        collected_at,
        collector_version,
        evidence_text="no <video>/YouTube/Vimeo embed found in fetched pages",
    )


def extract_signals(
    pages: list[FetchResult], collector_version: str, collected_at: str
) -> EvidenceSignals:
    """pages: list[FetchResult], pages[0] must be the homepage attempt."""
    evidence: dict[str, Evidence] = {}
    successful = _successful_pages(pages)

    evidence["https"] = _detect_https(pages, collected_at, collector_version)
    evidence["mobile_friendly"] = _detect_mobile_friendly(
        pages, collected_at, collector_version
    )
    evidence["customer_photos"] = _detect_customer_photos(
        pages, collected_at, collector_version
    )
    evidence["customer_videos"] = _detect_customer_videos(
        pages, collected_at, collector_version
    )

    for key, detector in _DETECTORS.items():
        scope_keywords = _SIGNAL_SCOPE_KEYWORDS[key]
        matched_snippet: Optional[str] = None
        matched_url: Optional[str] = None
        scope_page_seen = False
        for page in successful:
            assert page.text is not None  # guaranteed by _successful_pages
            if _page_matches_scope(
                page.final_url or page.requested_url, scope_keywords
            ):
                scope_page_seen = True
            snippet = detector(page.text)
            if snippet:
                matched_snippet = snippet
                matched_url = page.final_url
                break
        if matched_snippet:
            evidence[key] = Evidence.present(
                matched_url, matched_snippet, collected_at, collector_version
            )
        elif scope_page_seen:
            evidence[key] = Evidence.absent(
                successful[0].final_url if successful else None,
                collected_at,
                collector_version,
                confidence=0.85 if scope_keywords else 0.7,
                evidence_text="no match found in successfully-fetched page(s) targeted at this topic",
            )
        else:
            evidence[key] = Evidence.unknown(
                "no relevant page for this signal's topic was successfully fetched this run",
                collected_at,
                collector_version,
            )

    missing = set(WEBSITE_SIGNAL_KEYS) - set(evidence.keys())
    for key in missing:
        evidence[key] = Evidence.unknown(
            "extractor has no detector for this key", collected_at, collector_version
        )

    return EvidenceSignals(evidence)


def extract_social_links(pages: list[FetchResult]) -> dict[str, Optional[str]]:
    found: dict[str, Optional[str]] = {
        "instagram": None,
        "facebook": None,
        "youtube": None,
        "tiktok": None,
    }
    for page in _successful_pages(pages):
        assert page.text is not None  # guaranteed by _successful_pages
        for platform, pattern in SOCIAL_URL_RE.items():
            if found[platform] is None:
                m = pattern.search(page.text)
                if m:
                    found[platform] = m.group(0)
    return found


def extract_homepage_excerpt(pages: list[FetchResult], max_chars: int = 1500) -> str:
    successful = _successful_pages(pages)
    if not successful:
        return ""
    assert successful[0].text is not None  # guaranteed by _successful_pages
    text = re.sub(r"<[^>]+>", " ", successful[0].text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
