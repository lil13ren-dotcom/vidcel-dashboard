"""Evidence-aware scoring for Phase 1.1.

The core change from analysis/scoring.py: a signal that was never
confirmed (UNKNOWN/BLOCKED/ERROR) must not be scored as if it were a
confirmed absence. Every score here is computed only from the subset of
signals that were actually confirmed (`observed_score`), alongside a
`coverage_ratio` saying how much of the checklist that subset represents.
A score computed from 1/18 confirmed signals and a score computed from
17/18 are not the same claim, even if the arithmetic result is identical —
`decision_grade_score` is what gates that distinction downstream.
"""

from __future__ import annotations

from typing import Any, Optional, cast

from lighthouse.models import EvidenceSignals, RawCompanyV2

Score = tuple[Optional[float], float]  # (score, coverage)

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

DECISION_GRADE_COVERAGE_THRESHOLD = 0.6
COMPANY_DECISION_GRADE_COVERAGE_THRESHOLD = 0.5


def coverage_ratio(signals: EvidenceSignals, keys: list[str]) -> float:
    if not keys:
        return 0.0
    confirmed = sum(1 for k in keys if signals.is_confirmed(k))
    return confirmed / len(keys)


def observed_score(signals: EvidenceSignals, keys: list[str]) -> Optional[float]:
    confirmed = [k for k in keys if signals.is_confirmed(k)]
    if not confirmed:
        return None
    present = sum(1 for k in confirmed if signals.is_present(k))
    return 100.0 * present / len(confirmed)


def mean_confidence(signals: EvidenceSignals, keys: list[str]) -> float:
    confirmed = [k for k in keys if signals.is_confirmed(k)]
    if not confirmed:
        return 0.0
    return sum(signals.confidence(k) for k in confirmed) / len(confirmed)


def decision_grade_score(
    score: Optional[float],
    coverage: float,
    threshold: float = DECISION_GRADE_COVERAGE_THRESHOLD,
) -> Optional[float]:
    if score is None or coverage < threshold:
        return None
    return score


def google_score(company: RawCompanyV2) -> Score:
    """(score, coverage). Unchanged math from v1 — Phase 1.1 scoped to
    website acquisition, not ratings acquisition (tracked separately in
    Backlog.md)."""
    if company.rating is None or company.review_count is None:
        return None, 0.0
    rating_component = 70.0 * (min(company.rating, 5.0) / 5.0)
    volume_component = 30.0 * (min(company.review_count, 200) / 200.0)
    return rating_component + volume_component, 1.0


def website_score(company: RawCompanyV2) -> Score:
    s = company.website_signals
    return observed_score(s, WEBSITE_CORE_SIGNALS), coverage_ratio(
        s, WEBSITE_CORE_SIGNALS
    )


def trust_score(company: RawCompanyV2) -> Score:
    s = company.website_signals
    return observed_score(s, TRUST_SIGNALS), coverage_ratio(s, TRUST_SIGNALS)


def proof_score(company: RawCompanyV2) -> Score:
    s = company.website_signals
    return observed_score(s, PROOF_SIGNALS), coverage_ratio(s, PROOF_SIGNALS)


def _pages_were_inspected(company: RawCompanyV2) -> bool:
    return company.acquisition.pages_fetched > 0


def social_score(company: RawCompanyV2) -> Score:
    """Coverage here isn't about a fixed signal list — it's about whether
    we ever got a page to look at. If acquisition never returned a single
    successfully-fetched page, we cannot claim to know whether social
    links exist or not.
    """
    if not _pages_were_inspected(company):
        return None, 0.0
    weights = {"facebook": 20, "instagram": 20, "youtube": 30, "tiktok": 30}
    score = sum(
        w for platform, w in weights.items() if getattr(company.social, platform)
    )
    return float(score), 1.0


def video_score(company: RawCompanyV2) -> Score:
    s = company.website_signals
    if not _pages_were_inspected(company) and not s.is_confirmed("customer_videos"):
        return None, 0.0
    score = 0.0
    if s.is_present("customer_videos"):
        score += 40.0
    if company.social.youtube:
        score += 30.0
    if company.social.tiktok:
        score += 30.0
    coverage = (
        1.0
        if _pages_were_inspected(company)
        else coverage_ratio(s, ["customer_videos"])
    )
    return score, coverage


def score_company(company: RawCompanyV2) -> dict[str, Any]:
    """Returns everything ScoredCompanyV2 needs: per-category
    (observed_score, coverage, decision_grade_score), plus the rolled-up
    overall opportunity score and its own decision-grade gate.
    """
    categories = {
        "google_score": google_score(company),
        "website_score": website_score(company),
        "trust_score": trust_score(company),
        "proof_score": proof_score(company),
        "social_score": social_score(company),
        "video_score": video_score(company),
    }

    observed = {name: val[0] for name, val in categories.items()}
    coverage = {name: val[1] for name, val in categories.items()}
    decision_grade = {
        name: decision_grade_score(val[0], val[1]) is not None
        for name, val in categories.items()
    }

    gap_categories = [
        "website_score",
        "trust_score",
        "proof_score",
        "social_score",
        "video_score",
    ]
    decision_grade_gap_categories = [c for c in gap_categories if decision_grade[c]]

    reasons = []
    overall = None
    if not decision_grade_gap_categories:
        reasons.append(
            "no website-derived category met the decision-grade coverage threshold"
        )
    elif not decision_grade["google_score"]:
        reasons.append(
            "rating/review_count not confirmed, so demand (and therefore overall opportunity) is unscorable"
        )
    else:
        # Every category in decision_grade_gap_categories, and
        # "google_score" (checked above), passed decision_grade_score()
        # gating, which only returns non-None when the underlying score is
        # non-None — so these casts reflect an invariant already enforced
        # above, not an unchecked assumption.
        maturity = sum(
            cast(float, observed[c]) for c in decision_grade_gap_categories
        ) / len(decision_grade_gap_categories)
        demand = cast(float, observed["google_score"]) / 100.0
        gap = 1.0 - (maturity / 100.0)
        overall = 100.0 * demand * gap
        if len(decision_grade_gap_categories) < len(gap_categories):
            missing = set(gap_categories) - set(decision_grade_gap_categories)
            reasons.append(
                f"computed from {len(decision_grade_gap_categories)}/{len(gap_categories)} "
                f"categories with sufficient coverage (missing: {', '.join(sorted(missing))})"
            )

    all_coverages = list(coverage.values())
    data_coverage_ratio = (
        sum(all_coverages) / len(all_coverages) if all_coverages else 0.0
    )
    data_confidence = mean_confidence(
        company.website_signals, WEBSITE_CORE_SIGNALS + PROOF_SIGNALS + TRUST_SIGNALS
    )

    is_decision_grade = (
        overall is not None
        and data_coverage_ratio >= COMPANY_DECISION_GRADE_COVERAGE_THRESHOLD
    )
    if (
        overall is not None
        and data_coverage_ratio < COMPANY_DECISION_GRADE_COVERAGE_THRESHOLD
    ):
        reasons.append(
            f"overall data coverage {data_coverage_ratio:.0%} is below the "
            f"{COMPANY_DECISION_GRADE_COVERAGE_THRESHOLD:.0%} company-level threshold"
        )
    if not reasons:
        reasons.append("all categories met their coverage threshold")

    return {
        "observed_score": observed,
        "coverage_ratio": coverage,
        "decision_grade": decision_grade,
        "overall_opportunity_score": overall,
        "data_coverage_ratio": data_coverage_ratio,
        "data_confidence": data_confidence,
        "is_decision_grade": is_decision_grade,
        "decision_grade_reason": "; ".join(reasons),
    }
