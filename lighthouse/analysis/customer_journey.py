"""Maps collected facts onto the customer journey funnel from the brief:

    Google Search -> Google Reviews -> Website -> Portfolio -> Contact

For each step: what builds trust, what kills it, what's simply missing.
Each rule below is a direct, fixed mapping from a fact to a bucket — no
generative reasoning, so the same inputs always produce the same journey
notes.
"""

from __future__ import annotations

from lighthouse.models import RawCompany

STEPS = ["Google Search", "Google Reviews", "Website", "Portfolio", "Contact"]

JourneyStep = dict[str, list[str]]


def _search_step(c: RawCompany) -> JourneyStep:
    if c.google_maps_url is None:
        return {
            "builders": [],
            "killers": [],
            "missing": ["No confirmed Google Business Profile found"],
        }
    return {
        "builders": ["Has an active Google Business Profile"],
        "killers": [],
        "missing": [],
    }


def _reviews_step(c: RawCompany) -> JourneyStep:
    builders: list[str] = []
    killers: list[str] = []
    missing: list[str] = []
    if c.rating is None or c.review_count is None:
        missing.append("Rating/review count not publicly confirmed")
        return {"builders": builders, "killers": killers, "missing": missing}
    if c.rating >= 4.5 and c.review_count >= 50:
        builders.append(
            f"{c.rating}★ across {c.review_count} reviews reads as established and trustworthy"
        )
    if c.rating < 4.0:
        killers.append(
            f"{c.rating}★ average is below the trust threshold most buyers use to filter"
        )
    if c.review_count < 10:
        killers.append(
            f"Only {c.review_count} reviews — too thin to establish trust at a glance"
        )
    return {"builders": builders, "killers": killers, "missing": missing}


def _website_step(c: RawCompany) -> JourneyStep:
    s = c.website_signals
    builders: list[str] = []
    killers: list[str] = []
    missing: list[str] = []
    if s.https and s.cta:
        builders.append("HTTPS + clear call-to-action on arrival")
    if not s.https:
        killers.append("No HTTPS — browsers flag this as Not Secure")
    if not s.cta:
        killers.append("No clear call-to-action on the homepage")
    if not s.mobile_friendly:
        killers.append("Not mobile-friendly, and most local search traffic is mobile")
    if not s.about_us:
        missing.append("No About Us page — buyer can't tell who they're hiring")
    if not s.financing:
        missing.append("No financing messaging")
    if not s.warranty:
        missing.append("No warranty/guarantee messaging")
    return {"builders": builders, "killers": killers, "missing": missing}


def _portfolio_step(c: RawCompany) -> JourneyStep:
    s = c.website_signals
    builders: list[str] = []
    killers: list[str] = []
    missing: list[str] = []
    proof_present = [
        k
        for k in ["portfolio", "before_after", "testimonials", "customer_photos"]
        if getattr(s, k)
    ]
    if len(proof_present) >= 3:
        builders.append("Strong visual proof: " + ", ".join(proof_present))
    if not proof_present:
        killers.append("Zero visual proof of past work anywhere on the site")
    for k, label in [
        ("portfolio", "portfolio/gallery"),
        ("before_after", "before/after photos"),
        ("testimonials", "written testimonials"),
        ("customer_videos", "customer videos"),
    ]:
        if not getattr(s, k):
            missing.append(f"No {label}")
    return {"builders": builders, "killers": killers, "missing": missing}


def _contact_step(c: RawCompany) -> JourneyStep:
    s = c.website_signals
    builders: list[str] = []
    killers: list[str] = []
    missing: list[str] = []
    if s.quote_form and c.phone:
        builders.append("Quote form and phone number both available")
    if not s.quote_form and not s.contact_form:
        killers.append("No way to request a quote or contact the business on the site")
    if not c.phone:
        missing.append("No phone number listed")
    if not c.email:
        missing.append("No public email listed")
    return {"builders": builders, "killers": killers, "missing": missing}


_STEP_FUNCS = {
    "Google Search": _search_step,
    "Google Reviews": _reviews_step,
    "Website": _website_step,
    "Portfolio": _portfolio_step,
    "Contact": _contact_step,
}


def build_journey(company: RawCompany) -> dict[str, JourneyStep]:
    journey: dict[str, JourneyStep] = {}
    for step in STEPS:
        result = _STEP_FUNCS[step](company)
        journey[step] = {
            "builders": result.get("builders", []),
            "killers": result.get("killers", []),
            "missing": result.get("missing", []),
        }
    return journey
