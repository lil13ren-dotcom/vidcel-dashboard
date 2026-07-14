"""Turns missing signals into a ranked, prioritized opportunity list.

Every opportunity in CATALOG is a fixed rule: (trigger condition) ->
(title, reason template, impact, difficulty, AI automation potential).
Nothing here is generated per-company by an LLM — the catalog is written
once, and each company simply "lights up" whichever rules its facts
trigger. This is what "AI automation potential" means throughout: how
automatable the *fix* is (e.g. an AI video generator could produce a
trust video), not a comment on this codebase.

Ranking: priority = impact_weight / difficulty_weight, so cheap+high-impact
fixes surface first. Ties broken by catalog order.
"""

from __future__ import annotations

from typing import Callable, TypedDict

from lighthouse.models import RawCompany, Opportunity

_IMPACT_WEIGHT = {"High": 3, "Medium": 2, "Low": 1}
_DIFFICULTY_WEIGHT = {"Low": 1, "Medium": 2, "High": 3}


def _trigger_missing(*keys: str) -> Callable[[RawCompany], bool]:
    def check(c: RawCompany) -> bool:
        return any(not getattr(c.website_signals, k) for k in keys)

    return check


class Rule(TypedDict):
    title: str
    trigger: Callable[[RawCompany], bool]
    reason: str
    impact: str
    difficulty: str
    ai_automation: str


CATALOG: list[Rule] = [
    {
        "title": "Homepage Rewrite & Clear CTA",
        "trigger": _trigger_missing("cta", "about_us"),
        "reason": "Homepage lacks a clear call-to-action and/or an About Us section, so first-time visitors can't tell what to do next or who they're hiring.",
        "impact": "High",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Before / After Gallery",
        "trigger": _trigger_missing("before_after"),
        "reason": "Before/after photos were not found or not confirmable during this research pass (worth a direct site check) — the single strongest proof format for visually-driven trades like roofing, HVAC, and remodeling.",
        "impact": "High",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "On-Site Review / Testimonial Section",
        "trigger": _trigger_missing("testimonials"),
        "reason": "Reviews live on Google but are never surfaced on the site itself, so site visitors don't see the reputation the business has already earned.",
        "impact": "High",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Customer Trust Video",
        "trigger": lambda c: (
            not c.website_signals.customer_videos and not c.social.youtube
        ),
        "reason": "No customer testimonial or project video anywhere — video converts better than any other proof format and this business has none.",
        "impact": "High",
        "difficulty": "Medium",
        "ai_automation": "High",
    },
    {
        "title": "Google Review Generation + Google Posts",
        "trigger": lambda c: (c.review_count or 0) < 50 or (c.rating or 0) < 4.5,
        "reason": "Review volume or rating is below the threshold buyers use to filter local providers at a glance.",
        "impact": "Medium",
        "difficulty": "Low",
        "ai_automation": "Medium",
    },
    {
        "title": "Financing Messaging",
        "trigger": _trigger_missing("financing"),
        "reason": "No financing/payment plan messaging, which matters for high-ticket jobs like roofs, HVAC systems, and remodels.",
        "impact": "Medium",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Warranty & Certification Badges",
        "trigger": _trigger_missing("warranty", "certifications"),
        "reason": "Warranty and/or certification/association membership isn't communicated, leaving a credibility gap versus competitors who display it.",
        "impact": "Medium",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Team / About Page",
        "trigger": _trigger_missing("team_page"),
        "reason": "No page introduces the actual people doing the work — buyers hiring for their home want to know who's showing up.",
        "impact": "Medium",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "FAQ Page",
        "trigger": _trigger_missing("faq"),
        "reason": "No FAQ section to pre-empt common objections (cost, timeline, process), leaving buyers to call and ask or bounce.",
        "impact": "Low",
        "difficulty": "Low",
        "ai_automation": "High",
    },
    {
        "title": "Quote Form Optimization",
        "trigger": _trigger_missing("quote_form"),
        "reason": "No dedicated quote/estimate request form — the highest-intent conversion path on a home-services site is missing.",
        "impact": "High",
        "difficulty": "Low",
        "ai_automation": "Medium",
    },
    {
        "title": "Service Area / Local SEO Pages",
        "trigger": _trigger_missing("service_area"),
        "reason": "No explicit list of cities/areas served, which weakens both buyer confidence and local search visibility.",
        "impact": "Medium",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "Social Video Presence (Instagram/TikTok)",
        "trigger": lambda c: not c.social.instagram and not c.social.tiktok,
        "reason": "No presence on the two platforms where homeowners increasingly discover local contractors through short-form video.",
        "impact": "Medium",
        "difficulty": "Medium",
        "ai_automation": "High",
    },
    {
        "title": "Case Studies",
        "trigger": _trigger_missing("case_studies"),
        "reason": "No detailed project write-ups — case studies convert higher-consideration buyers who want specifics, not just photos.",
        "impact": "Medium",
        "difficulty": "Medium",
        "ai_automation": "Medium",
    },
    {
        "title": "Mobile Optimization",
        "trigger": _trigger_missing("mobile_friendly"),
        "reason": "Mobile-friendliness could not be confirmed during this research pass and should be checked directly (this requires rendering the live page) — most local-service searches happen on a phone, so it's worth verifying first.",
        "impact": "High",
        "difficulty": "Medium",
        "ai_automation": "Low",
    },
]


# Maps an opportunity title to a sellable product/service and a one-line
# outreach angle template. Fixed mapping, not per-company generation — the
# {name} placeholder is filled in with the company's own name so outreach
# reads as researched rather than templated.
SUGGESTED_PRODUCT = {
    "Homepage Rewrite & Clear CTA": "Homepage Video Hero + Copy Refresh",
    "Before / After Gallery": "Before/After Photo & Video Gallery Package",
    "On-Site Review / Testimonial Section": "Review Showcase Video & Site Widget",
    "Customer Trust Video": "Customer Trust Video Package",
    "Google Review Generation + Google Posts": "Review Generation & Google Posts Service",
    "Financing Messaging": "Financing Explainer Video + Landing Section",
    "Warranty & Certification Badges": "Trust Badge & Credentials Refresh",
    "Team / About Page": "Meet-the-Team Video + About Page",
    "FAQ Page": "FAQ Video Series + Page",
    "Quote Form Optimization": "Quote Funnel Video + Form Redesign",
    "Service Area / Local SEO Pages": "Local Service-Area Landing Pages",
    "Social Video Presence (Instagram/TikTok)": "Short-Form Video Content Package (Reels/TikTok)",
    "Case Studies": "Project Case Study Video Series",
    "Mobile Optimization": "Mobile Site Rebuild",
}

OUTREACH_ANGLE = {
    "Homepage Rewrite & Clear CTA": "\"{name}, your reviews say you're great — your homepage doesn't say anything at all. Let's fix that first.\"",
    "Before / After Gallery": '"{name} does work customers love, but nobody can see it before they call. A before/after gallery turns your best jobs into your best sales pitch."',
    "On-Site Review / Testimonial Section": '"{name} has real reviews earning real trust on Google — but none of it shows up on your own site."',
    "Customer Trust Video": '"A 60-second customer video on {name}\'s homepage would do more to convert visitors than any amount of text."',
    "Google Review Generation + Google Posts": '"{name}\'s review count is holding back how many calls you get from Google search alone."',
    "Financing Messaging": '"Big-ticket jobs stall on price shock. {name} isn\'t telling customers financing is an option."',
    "Warranty & Certification Badges": '"{name} is certified/warrantied but not saying so — that\'s a free trust signal being left on the table."',
    "Team / About Page": "\"People let strangers into their home. {name} isn't showing them who's coming.\"",
    "FAQ Page": '"Every call {name} gets asking the same 3 questions is a call an FAQ page could have converted without picking up the phone."',
    "Quote Form Optimization": '"{name}\'s highest-intent visitors have no fast way to request a quote on the site."',
    "Service Area / Local SEO Pages": '"{name} isn\'t clearly telling Google — or customers — exactly where it works."',
    "Social Video Presence (Instagram/TikTok)": '"{name}\'s next customers are scrolling Instagram and TikTok for a contractor right now."',
    "Case Studies": '"Bigger jobs need bigger proof. {name} has none published."',
    "Mobile Optimization": "\"Most of {name}'s traffic is on a phone, and the site isn't built for one.\"",
}


def build_opportunities(company: RawCompany, top_n: int = 5) -> list[Opportunity]:
    triggered: list[Opportunity] = []
    for rule in CATALOG:
        if rule["trigger"](company):
            priority = (
                _IMPACT_WEIGHT[rule["impact"]] / _DIFFICULTY_WEIGHT[rule["difficulty"]]
            )
            triggered.append(
                Opportunity(
                    company_id=company.id,
                    title=rule["title"],
                    reason=rule["reason"],
                    expected_impact=rule["impact"],
                    estimated_difficulty=rule["difficulty"],
                    ai_automation_potential=rule["ai_automation"],
                    priority_score=round(priority, 2),
                )
            )
    triggered.sort(key=lambda o: o.priority_score, reverse=True)
    return triggered[:top_n]
