"""Markdown deliverables: per-company reports and the industry summary.

Strengths/weaknesses lists are derived mechanically from which signals are
present/absent (models.SIGNAL_LABELS) — the only free-composed text is the
opportunity reasons and outreach angles, both of which come from the fixed
catalog in analysis/opportunity_engine.py, not from per-company generation.
"""
from __future__ import annotations

import os
import statistics as stats

from lighthouse.models import ScoredCompany, WEBSITE_SIGNAL_KEYS, SIGNAL_LABELS, RENDER_ONLY_SIGNAL_KEYS
from lighthouse.analysis.opportunity_engine import SUGGESTED_PRODUCT, OUTREACH_ANGLE

DATA_COLLECTION_CAVEAT = (
    "**Data collection note:** in this Phase 1 run, direct page-rendering "
    "access (`WebFetch`) was unavailable, so website signals were "
    "reconstructed from search-result snippets rather than the live page. "
    "That method can confirm most signals (a page titled \"Testimonials\" or "
    "\"Financing\" turning up in search is good evidence), but it cannot "
    "confirm signals that require actually seeing the rendered page: "
    "**mobile-friendliness, before/after photos, and customer-submitted "
    "photos**. Those three show `false` for every company in this sample — "
    "read that as *not verified this run*, not *confirmed absent*. See "
    "`docs/lighthouse/Decision_Log.md` for detail. Everything else below is "
    "search-confirmed evidence, not a guess."
)


def _present_absent(company) -> tuple:
    present = [SIGNAL_LABELS[k] for k in WEBSITE_SIGNAL_KEYS if getattr(company.website_signals, k)]
    absent = [
        SIGNAL_LABELS[k] for k in WEBSITE_SIGNAL_KEYS
        if not getattr(company.website_signals, k) and k not in RENDER_ONLY_SIGNAL_KEYS
    ]
    unverified = [
        SIGNAL_LABELS[k] for k in RENDER_ONLY_SIGNAL_KEYS
        if not getattr(company.website_signals, k)
    ]
    return present, absent, unverified


def write_company_report(sc: ScoredCompany, path: str) -> None:
    c = sc.company
    present, absent, unverified = _present_absent(c)
    top_opp = sc.opportunities[0] if sc.opportunities else None
    product = SUGGESTED_PRODUCT.get(top_opp.title, "Digital Trust Audit") if top_opp else "Digital Trust Audit"
    angle = (OUTREACH_ANGLE.get(top_opp.title, "\"{name}, there's a clear gap between how good you are and how that shows up online.\"")
              .format(name=c.name)) if top_opp else ""

    lines = []
    lines.append(f"# {c.name} — Lighthouse Report")
    lines.append("")
    lines.append(f"**Industry:** {c.industry}  ")
    lines.append(f"**Location:** {c.city}, {c.state}  ")
    lines.append(f"**Website:** {c.website}  ")
    lines.append("")
    lines.append(f"> {DATA_COLLECTION_CAVEAT}")
    lines.append("")
    if c.rating is not None and c.review_count is not None:
        lines.append(f"**Google:** {c.rating}★ ({c.review_count} reviews)  ")
    else:
        lines.append("**Google:** rating/review count not publicly confirmed  ")
    lines.append("")
    lines.append("## Scores")
    lines.append("")
    lines.append("| Metric | Score /100 |")
    lines.append("|---|---|")
    lines.append(f"| Google Score | {round(sc.google_score, 1)} |")
    lines.append(f"| Website Score | {round(sc.website_score, 1)} |")
    lines.append(f"| Trust Score | {round(sc.trust_score, 1)} |")
    lines.append(f"| Proof Score | {round(sc.proof_score, 1)} |")
    lines.append(f"| Social Score | {round(sc.social_score, 1)} |")
    lines.append(f"| Video Score | {round(sc.video_score, 1)} |")
    lines.append(f"| **Overall Opportunity Score** | **{round(sc.overall_opportunity_score, 1)}** |")
    lines.append("")
    lines.append("## Strengths")
    lines.append("")
    if present:
        for p in present:
            lines.append(f"- {p}")
    else:
        lines.append("- No trust signals detected on-site.")
    lines.append("")
    lines.append("## Weaknesses")
    lines.append("")
    if absent:
        for a in absent:
            lines.append(f"- Missing: {a}")
    else:
        lines.append("- No confirmed gaps against the core signal checklist.")
    if unverified:
        lines.append("")
        lines.append("**Not verified this run (requires a live page render — do not state these as fact):**")
        for u in unverified:
            lines.append(f"- {u}")
    lines.append("")

    if sc.top_customer_words:
        lines.append("## What Customers Actually Say")
        lines.append("")
        lines.append(f"Most repeated words in public reviews: {', '.join(sc.top_customer_words)}")
        lines.append("")

    if sc.high_opportunity_gaps:
        lines.append("## High Opportunity: Customer Language the Website Never Uses")
        lines.append("")
        for w in sc.high_opportunity_gaps:
            lines.append(f"- Customers say **\"{w}\"** — the homepage never mentions it")
        lines.append("")

    lines.append("## Customer Journey")
    lines.append("")
    for step, notes in sc.journey.items():
        lines.append(f"**{step}**")
        for b in notes["builders"]:
            lines.append(f"- ✅ Trust builder: {b}")
        for k in notes["killers"]:
            lines.append(f"- ❌ Trust killer: {k}")
        for m in notes["missing"]:
            lines.append(f"- ⚪ Missing: {m}")
        lines.append("")

    lines.append("## Biggest Opportunity")
    lines.append("")
    if top_opp:
        lines.append(f"**{top_opp.title}** (Impact: {top_opp.expected_impact}, "
                      f"Difficulty: {top_opp.estimated_difficulty}, "
                      f"AI Automation Potential: {top_opp.ai_automation_potential})")
        lines.append("")
        lines.append(top_opp.reason)
    else:
        lines.append("No significant gaps triggered against the current catalog.")
    lines.append("")

    lines.append("## Top 5 Opportunities")
    lines.append("")
    for i, opp in enumerate(sc.opportunities, 1):
        lines.append(f"{i}. **{opp.title}** — {opp.reason} "
                      f"(Impact: {opp.expected_impact}, Difficulty: {opp.estimated_difficulty}, "
                      f"AI Automation: {opp.ai_automation_potential})")
    lines.append("")

    lines.append("## Suggested Product")
    lines.append("")
    lines.append(product)
    lines.append("")

    lines.append("## Suggested Outreach Angle")
    lines.append("")
    lines.append(angle)
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def write_industry_summary(scored: list, path: str) -> None:
    industries = sorted(set(sc.company.industry for sc in scored))
    lines = ["# Project Lighthouse — Industry Summary (Phase 1 POC)", ""]
    lines.append(f"Companies analyzed: **{len(scored)}** across {len(industries)} industries.")
    lines.append("")
    lines.append(f"> {DATA_COLLECTION_CAVEAT}")
    lines.append("")

    for industry in industries:
        group = [sc for sc in scored if sc.company.industry == industry]
        lines.append(f"## {industry} ({len(group)} companies)")
        lines.append("")

        avg = lambda attr: round(stats.mean(getattr(sc, attr) for sc in group), 1)
        lines.append("| Metric | Industry Average |")
        lines.append("|---|---|")
        for label, attr in [
            ("Google Score", "google_score"), ("Website Score", "website_score"),
            ("Trust Score", "trust_score"), ("Proof Score", "proof_score"),
            ("Social Score", "social_score"), ("Video Score", "video_score"),
            ("Overall Opportunity Score", "overall_opportunity_score"),
        ]:
            lines.append(f"| {label} | {avg(attr)} |")
        lines.append("")

        # Most common missing signals across the industry (excludes the
        # render-only signals that this run couldn't confirm either way —
        # see DATA_COLLECTION_CAVEAT above)
        gap_counts = {}
        for key in WEBSITE_SIGNAL_KEYS:
            if key in RENDER_ONLY_SIGNAL_KEYS:
                continue
            missing = sum(1 for sc in group if not getattr(sc.company.website_signals, key))
            if missing:
                gap_counts[key] = missing
        if gap_counts:
            lines.append("**Most common confirmed gaps:**")
            lines.append("")
            for key, count in sorted(gap_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]:
                pct = round(100 * count / len(group))
                lines.append(f"- {SIGNAL_LABELS[key]}: missing in {count}/{len(group)} companies ({pct}%)")
            lines.append("")

        # Most common triggered opportunities
        title_counts = {}
        for sc in group:
            for opp in sc.opportunities:
                title_counts[opp.title] = title_counts.get(opp.title, 0) + 1
        if title_counts:
            lines.append("**Most repeatable opportunities in this industry:**")
            lines.append("")
            for title, count in sorted(title_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]:
                lines.append(f"- {title} ({count}/{len(group)} companies)")
            lines.append("")

        ranked = sorted(group, key=lambda sc: sc.overall_opportunity_score, reverse=True)
        lines.append("**Ranked by Overall Opportunity Score:**")
        lines.append("")
        for sc in ranked:
            lines.append(f"- {sc.company.name} ({sc.company.city}, {sc.company.state}): "
                          f"{round(sc.overall_opportunity_score, 1)}")
        lines.append("")

    lines.append("## Cross-Industry Takeaway")
    lines.append("")
    by_industry_avg = sorted(
        industries,
        key=lambda ind: stats.mean(sc.overall_opportunity_score for sc in scored if sc.company.industry == ind),
        reverse=True,
    )
    top_industry = by_industry_avg[0]
    top_avg = round(stats.mean(sc.overall_opportunity_score for sc in scored if sc.company.industry == top_industry), 1)
    lines.append(f"**{top_industry}** shows the highest average Overall Opportunity Score in this POC sample "
                 f"({top_avg}/100) — the biggest combination of proven customer demand and weak digital trust "
                 f"presence, making it the strongest candidate industry to prioritize for outbound in Phase 2.")
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))
