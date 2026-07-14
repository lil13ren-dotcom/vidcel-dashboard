"""Deterministic, rule-based scoring.

Every function here is a pure function of RawCompany facts -> a number.
No LLM call, no subjective judgment — just point weights, so results are
reproducible and defensible ("why did this score 62?" always has a
numeric answer). This is intentional per the project brief: AI is used
upstream to *observe* facts (prompts/website_signal_prompt.py); it is
never used to *score* them.
"""

from __future__ import annotations

from lighthouse.models import RawCompany, WebsiteSignals

# --- category definitions -------------------------------------------------
# Each maps to one "Collect" bucket from the brief. Weights sum to 100
# within a category so scores are always 0-100 and comparable across
# companies and industries.

WEBSITE_CORE_SIGNALS = [
    "https",
    "mobile_friendly",
    "cta",
    "quote_form",
    "contact_form",
    "financing",
    "warranty",
    "faq",
    "about_us",
    "team_page",
    "certifications",
    "service_area",
]

PROOF_SIGNALS = [
    "portfolio",
    "case_studies",
    "before_after",
    "testimonials",
    "customer_photos",
    "customer_videos",
]

TRUST_SIGNALS = [
    "portfolio",
    "before_after",
    "team_page",
    "certifications",
    "warranty",
]


def _pct_present(signals: WebsiteSignals, keys: list[str]) -> float:
    present = sum(1 for k in keys if getattr(signals, k))
    return 100.0 * present / len(keys)


def google_score(company: RawCompany) -> float:
    """Legitimacy/demand signal: real rating * real review volume.

    Rating contributes 70% of the score (normalized against 5 stars),
    review volume contributes 30% (normalized against a 200-review cap —
    a home-services business with 200+ reviews is treated as maxed out).
    Missing data scores 0 rather than being imputed, since an unscored
    company should never look artificially strong.
    """
    if company.rating is None and company.review_count is None:
        return 0.0
    rating_component = 70.0 * (min(company.rating or 0.0, 5.0) / 5.0)
    volume_component = 30.0 * (min(company.review_count or 0, 200) / 200.0)
    return rating_component + volume_component


def website_score(company: RawCompany) -> float:
    """Core website trust/conversion infrastructure (12 signals)."""
    return _pct_present(company.website_signals, WEBSITE_CORE_SIGNALS)


def trust_score(company: RawCompany) -> float:
    """The 5 evidence types from the brief's Trust Analysis section, plus
    a reviews sub-score, averaged.
    """
    signal_component = _pct_present(company.website_signals, TRUST_SIGNALS)
    if company.rating is not None and company.review_count is not None:
        reviews_component = min(
            100.0,
            50.0 * (company.rating / 5.0)
            + 50.0 * min(company.review_count, 100) / 100.0,
        )
    else:
        reviews_component = 0.0
    # weight: 5 site-evidence types + 1 reviews component, equal weight
    return (signal_component * 5 + reviews_component) / 6.0


def proof_score(company: RawCompany) -> float:
    """The 6 "Proof" signals: portfolio, case studies, before/after, etc."""
    return _pct_present(company.website_signals, PROOF_SIGNALS)


def social_score(company: RawCompany) -> float:
    """Weighted toward video-capable platforms (YouTube/TikTok), since
    that is where a video-production opportunity is most visible.
    """
    weights = {"facebook": 20, "instagram": 20, "youtube": 30, "tiktok": 30}
    return sum(
        w for platform, w in weights.items() if getattr(company.social, platform)
    )


def video_score(company: RawCompany) -> float:
    """Is this business already using video as a trust asset at all?"""
    score = 0.0
    if company.website_signals.customer_videos:
        score += 40.0
    if company.social.youtube:
        score += 30.0
    if company.social.tiktok:
        score += 30.0
    return score


def overall_opportunity_score(company: RawCompany) -> float:
    """The single number the whole POC exists to produce.

    opportunity = demand (proof the business is real and busy) x gap
    (how far its digital trust presence is from where it could be).

    A company with great reviews but a weak website is the ideal
    sales target: proven demand, obvious gap. A company with no
    reviews and a weak website is not a good target yet — there may be
    no real business behind it. A company with great reviews AND a
    strong website is not a good target — there's no gap to sell into.
    """
    demand = min(google_score(company), 100.0) / 100.0
    maturity = (
        sum(
            [
                website_score(company),
                trust_score(company),
                proof_score(company),
                social_score(company),
                video_score(company),
            ]
        )
        / 5.0
    )
    gap = 1.0 - (maturity / 100.0)
    return 100.0 * demand * gap


def score_company(company: RawCompany) -> dict[str, float]:
    return {
        "google_score": google_score(company),
        "website_score": website_score(company),
        "trust_score": trust_score(company),
        "proof_score": proof_score(company),
        "social_score": social_score(company),
        "video_score": video_score(company),
        "overall_opportunity_score": overall_opportunity_score(company),
    }
