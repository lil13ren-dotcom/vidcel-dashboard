"""Customer language vs. website language gap detection.

Rule: if a trust word or repeated customer phrase shows up in reviews but
never appears in the site's own homepage copy, that's a "High Opportunity"
flag — the business already has the reputation, it just isn't saying it
about itself. Matching is plain case-insensitive substring search.
"""

from __future__ import annotations

from typing import Optional, Protocol

from lighthouse.analysis.review_intelligence import (
    top_customer_words,
    trust_signal_word_hits,
    has_sufficient_review_text,
)


class _HasHomepageAndReviews(Protocol):
    """Matches both RawCompany (v1) and RawCompanyV2 (Phase 1.1)."""

    review_snippets: list[str]
    homepage_text_excerpt: Optional[str]


def find_high_opportunity_gaps(company: _HasHomepageAndReviews) -> list[str]:
    """Words/phrases customers repeat that the homepage never mentions."""
    if not has_sufficient_review_text(company):
        return []

    homepage = (company.homepage_text_excerpt or "").lower()
    candidates = set(top_customer_words(company)) | set(
        trust_signal_word_hits(company).keys()
    )

    gaps = []
    for word in sorted(candidates):
        if word not in homepage:
            gaps.append(word)
    return gaps
