"""Evidence-aware customer journey mapping (Phase 1.1).

Same funnel as analysis/customer_journey.py (v1): Google Search -> Google
Reviews -> Website -> Portfolio -> Contact. The only change is that the
Website/Portfolio/Contact steps read signal *status*, not a bare bool, so
an unconfirmed signal lands in "missing" with honest wording instead of
silently becoming a trust killer.
"""

from __future__ import annotations

from lighthouse.models import RawCompanyV2

STEPS = ["Google Search", "Google Reviews", "Website", "Portfolio", "Contact"]

JourneyStep = dict[str, list[str]]


def _search_step(c: RawCompanyV2) -> JourneyStep:
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


def _reviews_step(c: RawCompanyV2) -> JourneyStep:
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


def _website_step(c: RawCompanyV2) -> JourneyStep:
    s = c.website_signals
    builders: list[str] = []
    killers: list[str] = []
    missing: list[str] = []

    if s.is_present("https") and s.is_present("cta"):
        builders.append("HTTPS + clear call-to-action confirmed on arrival")
    if s.is_absent("https"):
        killers.append("No HTTPS — browsers flag this as Not Secure")
    if s.is_absent("cta"):
        killers.append("No clear call-to-action found on the homepage")
    if s.is_absent("mobile_friendly"):
        killers.append(
            "No responsive viewport found — most local search traffic is mobile"
        )

    for key, label in [
        ("about_us", "About Us page"),
        ("financing", "financing messaging"),
        ("warranty", "warranty/guarantee messaging"),
    ]:
        if s.is_absent(key):
            missing.append(f"No {label}")
        elif not s.is_confirmed(key):
            missing.append(f"{label.capitalize()} not confirmed this run")

    if not c.acquisition.homepage_fetch_succeeded:
        missing.append(
            f"Homepage could not be directly inspected this run ({c.acquisition.homepage_status})"
        )

    return {"builders": builders, "killers": killers, "missing": missing}


def _portfolio_step(c: RawCompanyV2) -> JourneyStep:
    s = c.website_signals
    builders: list[str] = []
    killers: list[str] = []
    missing: list[str] = []
    proof_keys = ["portfolio", "before_after", "testimonials", "customer_photos"]
    confirmed_present = [k for k in proof_keys if s.is_present(k)]
    confirmed_absent = [k for k in proof_keys if s.is_absent(k)]
    unverified = [k for k in proof_keys if not s.is_confirmed(k)]

    if len(confirmed_present) >= 3:
        builders.append(
            "Strong confirmed visual proof: " + ", ".join(confirmed_present)
        )
    if confirmed_absent and len(confirmed_present) == 0:
        killers.append("Zero visual proof of past work confirmed anywhere on the site")

    labels = {
        "portfolio": "portfolio/gallery",
        "before_after": "before/after photos",
        "testimonials": "written testimonials",
        "customer_photos": "customer photos",
    }
    for k in confirmed_absent:
        missing.append(f"No {labels[k]}")
    for k in unverified:
        missing.append(f"{labels[k].capitalize()} not confirmed this run")

    return {"builders": builders, "killers": killers, "missing": missing}


def _contact_step(c: RawCompanyV2) -> JourneyStep:
    s = c.website_signals
    builders: list[str] = []
    killers: list[str] = []
    missing: list[str] = []
    if s.is_present("quote_form") and c.phone:
        builders.append("Quote form confirmed and phone number available")
    if s.is_absent("quote_form") and s.is_absent("contact_form"):
        killers.append(
            "No way to request a quote or contact the business confirmed on the site"
        )
    if not c.phone:
        missing.append("No phone number listed")
    if not c.email:
        missing.append("No public email listed")
    if not s.is_confirmed("quote_form") and not s.is_confirmed("contact_form"):
        missing.append("Quote/contact form presence not confirmed this run")
    return {"builders": builders, "killers": killers, "missing": missing}


_STEP_FUNCS = {
    "Google Search": _search_step,
    "Google Reviews": _reviews_step,
    "Website": _website_step,
    "Portfolio": _portfolio_step,
    "Contact": _contact_step,
}


def build_journey(company: RawCompanyV2) -> dict[str, JourneyStep]:
    return {step: _STEP_FUNCS[step](company) for step in STEPS}
