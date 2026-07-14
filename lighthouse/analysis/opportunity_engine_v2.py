"""Evidence-aware opportunity engine for Phase 1.1.

Same fixed-catalog design as analysis/opportunity_engine.py (v1), but every
trigger now distinguishes a *confirmed* gap (signal status == ABSENT) from
an *unverified* one (status == UNKNOWN/BLOCKED/ERROR) and phrases the
reason accordingly. Product/outreach-angle text is reused verbatim from
v1's fixed mapping — the message a rep would send doesn't change based on
which acquisition method found the gap, only how confidently it's stated.
"""

from __future__ import annotations

from typing import TypedDict

from lighthouse.models import EvidenceSignals, Opportunity, RawCompanyV2

_IMPACT_WEIGHT = {"High": 3, "Medium": 2, "Low": 1}
_DIFFICULTY_WEIGHT = {"Low": 1, "Medium": 2, "High": 3}

_UNVERIFIED_SUFFIX = " (not confirmed via direct site inspection this run — verify before using in outreach.)"


def _gap_status(signals: EvidenceSignals, keys: tuple[str, ...]) -> str:
    """'confirmed' if any key is a confirmed absence, 'unverified' if none
    are confirmed absent but at least one couldn't be confirmed either
    way, else 'none' (every key confirmed present)."""
    if any(signals.is_absent(k) for k in keys):
        return "confirmed"
    if any(not signals.is_confirmed(k) for k in keys):
        return "unverified"
    return "none"


class Rule(TypedDict):
    title: str
    keys: tuple[str, ...]
    reason: str
    impact: str
    difficulty: str
    ai_automation: str


CATALOG: list[Rule] = [
    {
        "title": "Homepage Rewrite & Clear CTA",
        "keys": ("cta", "about_us"),
        "reason": "Homepage lacks a clear call-to-action and/or an About Us section, so first-time visitors can't tell what to do next or who they're hiring.",
        "impact": "High",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Before / After Gallery",
        "keys": ("before_after",),
        "reason": "No before/after photos found — the single strongest proof format for visually-driven trades like roofing, HVAC, and remodeling.",
        "impact": "High",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "On-Site Review / Testimonial Section",
        "keys": ("testimonials",),
        "reason": "Reviews live on Google but are never surfaced on the site itself, so site visitors don't see the reputation the business has already earned.",
        "impact": "High",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Customer Trust Video",
        "keys": ("customer_videos",),
        "reason": "No customer testimonial or project video found on the site — video converts better than any other proof format and this business has none confirmed.",
        "impact": "High",
        "difficulty": "Medium",
        "ai_automation": "High",
    },
    {
        "title": "Financing Messaging",
        "keys": ("financing",),
        "reason": "No financing/payment plan messaging found, which matters for high-ticket jobs like roofs, HVAC systems, and remodels.",
        "impact": "Medium",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Warranty & Certification Badges",
        "keys": ("warranty", "certifications"),
        "reason": "Warranty and/or certification/association membership isn't communicated, leaving a credibility gap versus competitors who display it.",
        "impact": "Medium",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Team / About Page",
        "keys": ("team_page",),
        "reason": "No page introduces the actual people doing the work — buyers hiring for their home want to know who's showing up.",
        "impact": "Medium",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "FAQ Page",
        "keys": ("faq",),
        "reason": "No FAQ section found to pre-empt common objections (cost, timeline, process), leaving buyers to call and ask or bounce.",
        "impact": "Low",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Quote Form Optimization",
        "keys": ("quote_form",),
        "reason": "No dedicated quote/estimate request form found — the highest-intent conversion path on a home-services site is missing.",
        "impact": "High",
        "difficulty": "Low",
        "ai_automation": "Medium",
    },
    {
        "title": "Service Area / Local SEO Pages",
        "keys": ("service_area",),
        "reason": "No explicit list of cities/areas served found, which weakens both buyer confidence and local search visibility.",
        "impact": "Medium",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "Case Studies",
        "keys": ("case_studies",),
        "reason": "No detailed project write-ups found — case studies convert higher-consideration buyers who want specifics, not just photos.",
        "impact": "Medium",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "Mobile Optimization",
        "keys": ("mobile_friendly",),
        "reason": "Site does not present a responsive viewport, and most local-service searches happen on a phone.",
        "impact": "High",
        "difficulty": "Medium",
        "ai_automation": "Low",
    },
]


def _social_video_gap_status(company: RawCompanyV2) -> str:
    if not company.acquisition.pages_fetched:
        return "unverified"
    return (
        "confirmed"
        if not company.social.instagram and not company.social.tiktok
        else "none"
    )


def _review_generation_gap_status(company: RawCompanyV2) -> str:
    if company.rating is None or company.review_count is None:
        return "unverified"
    return (
        "confirmed" if (company.review_count < 50 or company.rating < 4.5) else "none"
    )


def build_opportunities(company: RawCompanyV2, top_n: int = 5) -> list[Opportunity]:
    triggered: list[Opportunity] = []

    for rule in CATALOG:
        status = _gap_status(company.website_signals, rule["keys"])
        if status == "none":
            continue
        reason = (
            rule["reason"]
            if status == "confirmed"
            else rule["reason"] + _UNVERIFIED_SUFFIX
        )
        confidence_discount = 1.0 if status == "confirmed" else 0.5
        priority = (
            confidence_discount
            * _IMPACT_WEIGHT[rule["impact"]]
            / _DIFFICULTY_WEIGHT[rule["difficulty"]]
        )
        triggered.append(
            Opportunity(
                company_id=company.id,
                title=rule["title"],
                reason=reason,
                expected_impact=rule["impact"],
                estimated_difficulty=rule["difficulty"],
                ai_automation_potential=rule["ai_automation"],
                priority_score=round(priority, 2),
            )
        )

    social_status = _social_video_gap_status(company)
    if social_status != "none":
        base = "No presence found on the two platforms where homeowners increasingly discover local contractors through short-form video."
        reason = base if social_status == "confirmed" else base + _UNVERIFIED_SUFFIX
        confidence_discount = 1.0 if social_status == "confirmed" else 0.5
        priority = (
            confidence_discount
            * _IMPACT_WEIGHT["Medium"]
            / _DIFFICULTY_WEIGHT["Medium"]
        )
        triggered.append(
            Opportunity(
                company_id=company.id,
                title="Social Video Presence (Instagram/TikTok)",
                reason=reason,
                expected_impact="Medium",
                estimated_difficulty="Medium",
                ai_automation_potential="High",
                priority_score=round(priority, 2),
            )
        )

    review_status = _review_generation_gap_status(company)
    if review_status != "none":
        base = "Review volume or rating is below the threshold buyers use to filter local providers at a glance."
        reason = (
            base
            if review_status == "confirmed"
            else base + " (rating/review count not confirmed this run)"
        )
        confidence_discount = 1.0 if review_status == "confirmed" else 0.5
        priority = (
            confidence_discount * _IMPACT_WEIGHT["Medium"] / _DIFFICULTY_WEIGHT["Low"]
        )
        triggered.append(
            Opportunity(
                company_id=company.id,
                title="Google Review Generation + Google Posts",
                reason=reason,
                expected_impact="Medium",
                estimated_difficulty="Low",
                ai_automation_potential="Medium",
                priority_score=round(priority, 2),
            )
        )

    triggered.sort(key=lambda o: o.priority_score, reverse=True)
    return triggered[:top_n]
