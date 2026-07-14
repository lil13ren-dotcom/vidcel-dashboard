"""Markdown deliverables for Phase 1.1 — company reports and industry
summary, rewritten around evidence status instead of plain booleans.
"""

from __future__ import annotations

import statistics as stats

from lighthouse.analysis.integrity_gate import GateResult
from lighthouse.analysis.opportunity_engine import OUTREACH_ANGLE, SUGGESTED_PRODUCT
from lighthouse.models import (
    RawCompanyV2,
    SIGNAL_LABELS,
    ScoredCompanyV2,
    WEBSITE_SIGNAL_KEYS,
)


def _confirmed_present(company: RawCompanyV2) -> list[str]:
    return [
        SIGNAL_LABELS[k]
        for k in WEBSITE_SIGNAL_KEYS
        if company.website_signals.is_present(k)
    ]


def _confirmed_absent(company: RawCompanyV2) -> list[str]:
    return [
        SIGNAL_LABELS[k]
        for k in WEBSITE_SIGNAL_KEYS
        if company.website_signals.is_absent(k)
    ]


def _unverified(company: RawCompanyV2) -> list[str]:
    return [
        SIGNAL_LABELS[k]
        for k in WEBSITE_SIGNAL_KEYS
        if not company.website_signals.is_confirmed(k)
    ]


def write_company_report(sc: ScoredCompanyV2, path: str) -> None:
    c = sc.company
    present, absent, unverified = (
        _confirmed_present(c),
        _confirmed_absent(c),
        _unverified(c),
    )
    top_opp = sc.opportunities[0] if sc.opportunities else None
    product = (
        SUGGESTED_PRODUCT.get(top_opp.title, "Digital Trust Audit")
        if top_opp
        else "Digital Trust Audit"
    )
    angle = (
        (
            OUTREACH_ANGLE.get(
                top_opp.title,
                '"{name}, there\'s a clear gap between how good you are and how that shows up online."',
            ).format(name=c.name)
        )
        if top_opp
        else ""
    )

    lines = [f"# {c.name} — Lighthouse Report (Phase 1.1, evidence-based)", ""]
    lines.append(f"**Industry:** {c.industry}  ")
    lines.append(f"**Location:** {c.city}, {c.state}  ")
    lines.append(f"**Website:** {c.website}  ")
    lines.append("")
    lines.append(
        f"> **Acquisition:** homepage fetch status = `{c.acquisition.homepage_status}` · "
        f"{c.acquisition.pages_fetched}/{c.acquisition.pages_attempted} pages successfully fetched · "
        f"method = `{c.acquisition.method_used}`"
        + (
            f" · blocked reason: {c.acquisition.blocked_reason}"
            if c.acquisition.blocked_reason
            else ""
        )
    )
    lines.append("")
    lines.append(
        f"**Decision grade:** {'YES' if sc.is_decision_grade else 'NO'} — {sc.decision_grade_reason}  "
    )
    lines.append(
        f"**Data coverage:** {sc.data_coverage_ratio:.0%} · **Data confidence:** {sc.data_confidence:.0%}  "
    )
    lines.append("")

    if c.rating is not None and c.review_count is not None:
        lines.append(f"**Google:** {c.rating}★ ({c.review_count} reviews)  ")
    else:
        lines.append("**Google:** rating/review count not publicly confirmed  ")
    lines.append("")

    lines.append("## Scores")
    lines.append("")
    lines.append("| Metric | Observed | Coverage | Decision-grade |")
    lines.append("|---|---|---|---|")
    for label, key in [
        ("Google Score", "google_score"),
        ("Website Score", "website_score"),
        ("Trust Score", "trust_score"),
        ("Proof Score", "proof_score"),
        ("Social Score", "social_score"),
        ("Video Score", "video_score"),
    ]:
        observed = sc.observed_score.get(key)
        coverage = sc.coverage_ratio.get(key, 0.0)
        grade = "yes" if sc.decision_grade.get(key) else "no"
        observed_str = f"{observed:.1f}" if observed is not None else "n/a"
        lines.append(f"| {label} | {observed_str} | {coverage:.0%} | {grade} |")
    overall_str = (
        f"{sc.overall_opportunity_score:.1f}"
        if sc.overall_opportunity_score is not None
        else "n/a (not decision-grade)"
    )
    lines.append(
        f"| **Overall Opportunity Score** | **{overall_str}** | {sc.data_coverage_ratio:.0%} | {'yes' if sc.is_decision_grade else 'no'} |"
    )
    lines.append("")

    lines.append("## Confirmed Present")
    lines.append("")
    for p in present or ["(none confirmed present)"]:
        lines.append(f"- {p}")
    lines.append("")

    lines.append("## Confirmed Absent")
    lines.append("")
    for a in absent or ["(no confirmed gaps)"]:
        lines.append(f"- Missing: {a}")
    lines.append("")

    if unverified:
        lines.append("## Not Verified This Run")
        lines.append("")
        lines.append(
            "Requires a successful page fetch that this run did not obtain — treat as unknown, not as fact:"
        )
        lines.append("")
        for u in unverified:
            lines.append(f"- {u}")
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
            lines.append(f"- ⚪ Missing/unverified: {m}")
        lines.append("")

    lines.append("## Top Opportunities")
    lines.append("")
    if sc.opportunities:
        for i, opp in enumerate(sc.opportunities, 1):
            lines.append(
                f"{i}. **{opp.title}** — {opp.reason} "
                f"(Impact: {opp.expected_impact}, Difficulty: {opp.estimated_difficulty}, "
                f"AI Automation: {opp.ai_automation_potential})"
            )
    else:
        lines.append("No opportunities triggered against current evidence.")
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


def write_industry_summary(
    scored: list[ScoredCompanyV2], gate_result: GateResult, path: str
) -> None:
    industries = sorted(set(sc.company.industry for sc in scored))
    lines = ["# Project Lighthouse — Industry Summary (Phase 1.1, evidence-based)", ""]
    lines.append(
        f"Companies analyzed: **{len(scored)}** across {len(industries)} industries."
    )
    lines.append("")
    lines.append(f"**Run status: {gate_result.run_status}**")
    lines.append("")
    if not gate_result.passed:
        lines.append(
            "> This run did **not** pass the Data Integrity Gate. The industry "
            "averages below are provided for transparency but must not be treated "
            "as validating any market hypothesis — see `acquisition_comparison.md` "
            "for why, and `docs/lighthouse/Decision_Log.md` for the root cause."
        )
        lines.append("")
    lines.append(
        "Gate metrics: " + ", ".join(f"{k}={v}" for k, v in gate_result.metrics.items())
    )
    lines.append("")

    decision_grade_scored = [sc for sc in scored if sc.is_decision_grade]
    lines.append(
        f"**{len(decision_grade_scored)}/{len(scored)}** companies are individually decision-grade. "
        "Aggregate statistics below use decision-grade companies only; non-decision-grade companies "
        "are listed separately per industry."
    )
    lines.append("")

    for industry in industries:
        group = [sc for sc in scored if sc.company.industry == industry]
        dg_group = [sc for sc in group if sc.is_decision_grade]
        lines.append(
            f"## {industry} ({len(group)} companies, {len(dg_group)} decision-grade)"
        )
        lines.append("")

        if dg_group:
            lines.append(
                "| Metric | Industry Average (decision-grade companies only) |"
            )
            lines.append("|---|---|")

            def avg(attr: str, dg_group: list[ScoredCompanyV2] = dg_group) -> float:
                return round(
                    float(
                        stats.mean(
                            getattr(sc, attr)
                            for sc in dg_group
                            if getattr(sc, attr) is not None
                        )
                    ),
                    1,
                )

            lines.append(
                f"| Overall Opportunity Score | {avg('overall_opportunity_score')} |"
            )
            lines.append(
                f"| Data Coverage | {round(stats.mean(sc.data_coverage_ratio for sc in dg_group), 2):.0%} |"
            )
            lines.append("")
        else:
            lines.append(
                "_No decision-grade companies in this industry this run — no aggregate average computed._"
            )
            lines.append("")

        lines.append("**Per-company status:**")
        lines.append("")
        for sc in sorted(
            group, key=lambda s: (not s.is_decision_grade, s.company.name)
        ):
            score_str = (
                f"{sc.overall_opportunity_score:.1f}"
                if sc.overall_opportunity_score is not None
                else "n/a"
            )
            lines.append(
                f"- {sc.company.name} ({sc.company.city}, {sc.company.state}): "
                f"opportunity={score_str}, decision_grade={sc.is_decision_grade}, "
                f"coverage={sc.data_coverage_ratio:.0%}, homepage_status={sc.company.acquisition.homepage_status}"
            )
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))
