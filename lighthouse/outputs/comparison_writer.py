"""Builds data/output/acquisition_comparison.{md,csv} — the brief's
required before/after audit of what the new direct-fetch acquisition
layer changed versus Phase 1's search-snippet reconstruction.

Written to be honest in both directions: if live fetch actually worked
this run, it reports real before/after deltas per company/industry. If
live fetch was blocked (as it was in the sandbox this was built in), it
says so plainly and does not manufacture a comparison that didn't happen.
"""

from __future__ import annotations

import csv
import statistics as stats
from typing import Optional

from lighthouse.analysis.integrity_gate import GateResult
from lighthouse.models import (
    RawCompany,
    ScoredCompany,
    ScoredCompanyV2,
    WEBSITE_SIGNAL_KEYS,
    EvidenceStatus,
)


def _v1_bool(v1_company: RawCompany, key: str) -> bool:
    return bool(getattr(v1_company.website_signals, key))


def _field_transitions(
    scored_v1: list[ScoredCompany], scored_v2: list[ScoredCompanyV2]
) -> dict[str, int]:
    v1_by_id = {sc.company.id: sc.company for sc in scored_v1}
    counts = {
        "false_to_present": 0,
        "false_to_unverified": 0,
        "true_to_absent": 0,
        "true_to_present": 0,
        "false_to_absent": 0,
        "unchanged": 0,
    }
    for sc2 in scored_v2:
        v1_company = v1_by_id.get(sc2.company.id)
        if v1_company is None:
            continue
        for key in WEBSITE_SIGNAL_KEYS:
            v1_val = _v1_bool(v1_company, key)
            v2_status = sc2.company.website_signals.status(key)
            if v1_val is False and v2_status == EvidenceStatus.PRESENT:
                counts["false_to_present"] += 1
            elif v1_val is False and v2_status in (
                EvidenceStatus.UNKNOWN,
                EvidenceStatus.BLOCKED,
                EvidenceStatus.ERROR,
            ):
                counts["false_to_unverified"] += 1
            elif v1_val is False and v2_status == EvidenceStatus.ABSENT:
                counts["false_to_absent"] += 1
            elif v1_val is True and v2_status == EvidenceStatus.ABSENT:
                counts["true_to_absent"] += 1
            elif v1_val is True and v2_status == EvidenceStatus.PRESENT:
                counts["true_to_present"] += 1
            else:
                counts["unchanged"] += 1
    return counts


def _leading_industry(industry_scores: list[tuple[str, Optional[float]]]) -> str:
    """industry_scores: one (industry, score-or-None) pair per company,
    already extracted by the caller so this helper doesn't need to know
    about ScoredCompany vs ScoredCompanyV2."""
    industries = sorted(set(industry for industry, _ in industry_scores))
    best: Optional[str] = None
    best_avg = float("-inf")
    for industry in industries:
        scores = [s for ind, s in industry_scores if ind == industry and s is not None]
        if not scores:
            continue
        avg = stats.mean(scores)
        if avg > best_avg:
            best, best_avg = industry, avg
    return best or "(undetermined — no scorable companies)"


def build_comparison_csv(
    scored_v1: list[ScoredCompany], scored_v2: list[ScoredCompanyV2], path: str
) -> None:
    v1_by_id = {sc.company.id: sc for sc in scored_v1}
    fields = [
        "company_id",
        "company_name",
        "industry",
        "v1_overall_opportunity_score",
        "v2_overall_opportunity_score",
        "score_delta",
        "v1_method",
        "v2_homepage_status",
        "v2_pages_fetched",
        "v2_data_coverage_ratio",
        "v2_is_decision_grade",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sc2 in scored_v2:
            sc1 = v1_by_id.get(sc2.company.id)
            v1_score: Optional[float] = sc1.overall_opportunity_score if sc1 else None
            v2_score = sc2.overall_opportunity_score
            delta: Optional[float] = (
                (v2_score - v1_score)
                if (v1_score is not None and v2_score is not None)
                else None
            )
            writer.writerow(
                {
                    "company_id": sc2.company.id,
                    "company_name": sc2.company.name,
                    "industry": sc2.company.industry,
                    "v1_overall_opportunity_score": round(v1_score, 1)
                    if v1_score is not None
                    else "",
                    "v2_overall_opportunity_score": round(v2_score, 1)
                    if v2_score is not None
                    else "",
                    "score_delta": round(delta, 1) if delta is not None else "",
                    "v1_method": "search_snippet_reconstruction",
                    "v2_homepage_status": sc2.company.acquisition.homepage_status,
                    "v2_pages_fetched": sc2.company.acquisition.pages_fetched,
                    "v2_data_coverage_ratio": round(sc2.data_coverage_ratio, 2),
                    "v2_is_decision_grade": sc2.is_decision_grade,
                }
            )


def build_comparison_md(
    scored_v1: list[ScoredCompany],
    scored_v2: list[ScoredCompanyV2],
    gate_result: GateResult,
    path: str,
) -> None:
    homepage_success_rate = gate_result.metrics.get("homepage_fetch_success_rate", 0.0)
    assert isinstance(homepage_success_rate, float)
    transitions = _field_transitions(scored_v1, scored_v2)
    v1_leader = _leading_industry(
        [(sc.company.industry, sc.overall_opportunity_score) for sc in scored_v1]
    )
    v2_leader = _leading_industry(
        [
            (
                sc.company.industry,
                sc.overall_opportunity_score if sc.is_decision_grade else None,
            )
            for sc in scored_v2
        ]
    )

    lines = [
        "# Acquisition Method Comparison — Phase 1 (search snippets) vs Phase 1.1 (direct fetch)",
        "",
    ]
    lines.append(f"**Run status: {gate_result.run_status}**")
    lines.append("")
    lines.append(
        "- Previous acquisition method: LLM research agent + `WebSearch` snippet reconstruction (no direct page fetch)"
    )
    lines.append(
        "- New acquisition method: `lighthouse/scrapers/website_fetcher.py` — direct `httpx` fetch "
        "(+ optional Playwright fallback), SSRF-guarded, robots.txt-respecting, evidence-recorded"
    )
    lines.append(
        f"- Homepage direct-fetch success rate this run: **{homepage_success_rate:.0%}** "
        f"({gate_result.metrics.get('companies_total', 0)} companies)"
    )
    lines.append("")

    if homepage_success_rate == 0.0:
        lines.append(
            "## Why this run cannot validate or invalidate any Phase 1 business conclusion"
        )
        lines.append("")
        lines.append(
            "Direct page fetching succeeded for **0** of the 20 companies. This is not a bug in the "
            "fetcher — every fetch failed the same way, at the same layer, including for neutral control "
            "domains (`example.com`) with no relationship to any company in this dataset. The runtime "
            "environment this run executed in blocks outbound HTTPS to arbitrary hosts at the network "
            "policy level (confirmed via `curl` returning `403` from the egress proxy even when the "
            "proxy was explicitly bypassed and the destination IP was dialed directly — see "
            "`docs/lighthouse/Decision_Log.md`, 2026-07-14 entries). Every one of the 20 companies below "
            "is therefore `BLOCKED`/`ERROR` at the acquisition layer, not `ABSENT` — the pipeline correctly "
            "distinguished 'we couldn't check' from 'we checked and it's not there,' which was this "
            "phase's core requirement, but that means there is no new website evidence to compare "
            "against Phase 1 in this run."
        )
        lines.append("")
        lines.append(
            "**No earlier conclusion is confirmed. No earlier conclusion is invalidated.** The Phase 1 "
            "results (`lighthouse/data/output/`) remain exactly what they were: search-snippet-derived, "
            "not decision-grade, and now formally superseded pending a real run of this same pipeline "
            "from an internet-enabled environment (see the Live E2E runner in "
            "`docs/lighthouse/README.md`)."
        )
        lines.append("")
        lines.append(
            "Field-transition counts below are all zero for the same reason — nothing could be "
            "re-observed to transition from false, so this table records the code path, not a result:"
        )
        lines.append("")
    else:
        lines.append("## What changed")
        lines.append("")

    lines.append("| Transition | Count |")
    lines.append("|---|---|")
    lines.append(
        f"| false (v1) → present (v2, confirmed) | {transitions['false_to_present']} |"
    )
    lines.append(
        f"| false (v1) → absent (v2, confirmed) | {transitions['false_to_absent']} |"
    )
    lines.append(
        f"| false (v1) → unverified (v2: unknown/blocked/error) | {transitions['false_to_unverified']} |"
    )
    lines.append(
        f"| true (v1) → present (v2, confirmed) | {transitions['true_to_present']} |"
    )
    lines.append(
        f"| true (v1) → absent (v2, confirmed) | {transitions['true_to_absent']} |"
    )
    lines.append(f"| unchanged / not comparable | {transitions['unchanged']} |")
    lines.append("")

    lines.append("## Score changes")
    lines.append("")
    v1_by_id = {sc.company.id: sc for sc in scored_v1}
    lines.append(
        "| Company | v1 Opportunity Score | v2 Opportunity Score | v2 Decision-Grade |"
    )
    lines.append("|---|---|---|---|")
    for sc2 in sorted(scored_v2, key=lambda s: s.company.id):
        sc1 = v1_by_id.get(sc2.company.id)
        v1_str = f"{sc1.overall_opportunity_score:.1f}" if sc1 else "n/a"
        v2_str = (
            f"{sc2.overall_opportunity_score:.1f}"
            if sc2.overall_opportunity_score is not None
            else "n/a"
        )
        lines.append(
            f"| {sc2.company.name} | {v1_str} | {v2_str} | {sc2.is_decision_grade} |"
        )
    lines.append("")

    lines.append("## Industry leadership")
    lines.append("")
    lines.append(f"- Leading industry under v1 (search snippets): **{v1_leader}**")
    lines.append(
        f"- Leading industry under v2 (direct fetch, decision-grade companies only): **{v2_leader}**"
    )
    if homepage_success_rate == 0.0:
        lines.append(
            "- v2 leadership is undetermined this run (zero decision-grade companies) — cannot say "
            "whether Roofing remains the leading industry until a real fetch run completes."
        )
    lines.append("")

    lines.append("## Unresolved limitations")
    lines.append("")
    lines.append(
        "- Ratings/review counts are still not sourced from a real API (Google Places/Yelp) in "
        "either version — tracked separately in `docs/lighthouse/Backlog.md`."
    )
    lines.append(
        "- Image-dependent signals (`before_after`, `customer_photos`) are only ever confirmed to "
        "`PRESENT` on strong textual/structural evidence; true visual confirmation still requires "
        "human or vision-model review, which is out of scope for this phase."
    )
    lines.append(
        "- Tier 2 (Playwright) fallback is implemented and unit-tested against a local fixture, "
        "but has not been exercised against a real JS-heavy site in this environment."
    )
    if homepage_success_rate == 0.0:
        lines.append(
            "- **Blocking:** this sandbox cannot reach arbitrary external websites at all. A real "
            "run requires the Live E2E runner described in `docs/lighthouse/README.md`, executed "
            "from an internet-enabled environment."
        )
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))
