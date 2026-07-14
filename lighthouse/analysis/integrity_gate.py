"""Data Integrity Gate (Phase 1.1, brief section 7).

Runs after acquisition + scoring, over the whole batch, and decides
whether the run as a whole is DECISION_GRADE or NOT_DECISION_GRADE. This
is a batch-level judgment, separate from each company's own
`is_decision_grade` flag (a run can fail the gate even if a handful of
companies individually look fine, because the gate is also checking
things like "did we systematically misrepresent failures as absences").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lighthouse.analysis import scoring_v2
from lighthouse.models import (
    EvidenceStatus,
    RawCompanyV2,
    ScoredCompanyV2,
    WEBSITE_SIGNAL_KEYS,
)

HOMEPAGE_SUCCESS_THRESHOLD = 0.85
RELEVANT_PAGE_THRESHOLD = 0.75


@dataclass
class GateResult:
    passed: bool
    run_status: str  # "DECISION_GRADE" or "NOT_DECISION_GRADE"
    metrics: dict[str, object] = field(default_factory=dict)
    failure_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "run_status": self.run_status,
            "metrics": self.metrics,
            "failure_reasons": self.failure_reasons,
        }


def _homepage_success_rate(scored: list[ScoredCompanyV2]) -> float:
    if not scored:
        return 0.0
    return sum(
        1 for s in scored if s.company.acquisition.homepage_fetch_succeeded
    ) / len(scored)


def _relevant_page_rate(scored: list[ScoredCompanyV2]) -> float:
    if not scored:
        return 0.0
    return sum(1 for s in scored if s.company.acquisition.pages_fetched >= 2) / len(
        scored
    )


def _find_failure_as_absence_violations(scored: list[ScoredCompanyV2]) -> list[str]:
    """A page-fetch failure must never present as a confirmed absence.
    `https` is legitimately exempt: it's derived from the URL scheme of
    whatever response we did get (even a non-2xx one), not from page
    content, so it can be confirmed independent of `pages_fetched`.
    """
    violations = []
    for s in scored:
        if s.company.acquisition.pages_fetched > 0:
            continue
        for key in WEBSITE_SIGNAL_KEYS:
            if key == "https":
                continue
            if s.company.website_signals.status(key) == EvidenceStatus.ABSENT:
                violations.append(
                    f"{s.company.id}: '{key}' marked ABSENT despite zero pages successfully fetched"
                )
    return violations


def _find_incomplete_evidence(scored: list[ScoredCompanyV2]) -> list[str]:
    problems = []
    for s in scored:
        keys_present = set(s.company.website_signals.keys())
        missing = set(WEBSITE_SIGNAL_KEYS) - keys_present
        if missing:
            problems.append(
                f"{s.company.id}: no evidence entry at all for {sorted(missing)}"
            )
    return problems


def _check_deterministic_rerun(companies_v2: list[RawCompanyV2]) -> list[str]:
    problems = []
    for company in companies_v2:
        first = scoring_v2.score_company(company)
        second = scoring_v2.score_company(company)
        if first != second:
            problems.append(
                f"{company.id}: score_company() produced different output on an identical rerun"
            )
    return problems


def _find_missing_confidence(scored: list[ScoredCompanyV2]) -> list[str]:
    return [
        f"{s.company.id}: data_confidence missing"
        for s in scored
        if s.data_confidence is None
    ]


def evaluate(
    scored: list[ScoredCompanyV2], companies_v2: list[RawCompanyV2]
) -> GateResult:
    homepage_rate = _homepage_success_rate(scored)
    page_rate = _relevant_page_rate(scored)
    failure_as_absence = _find_failure_as_absence_violations(scored)
    incomplete_evidence = _find_incomplete_evidence(scored)
    nondeterminism = _check_deterministic_rerun(companies_v2)
    missing_confidence = _find_missing_confidence(scored)
    decision_grade_count = sum(1 for s in scored if s.is_decision_grade)

    reasons = []
    if homepage_rate < HOMEPAGE_SUCCESS_THRESHOLD:
        reasons.append(
            f"homepage direct-fetch success rate {homepage_rate:.0%} is below the "
            f"{HOMEPAGE_SUCCESS_THRESHOLD:.0%} minimum"
        )
    if page_rate < RELEVANT_PAGE_THRESHOLD:
        reasons.append(
            f"'at least one relevant page inspected' rate {page_rate:.0%} is below the "
            f"{RELEVANT_PAGE_THRESHOLD:.0%} minimum"
        )
    reasons.extend(
        f"acquisition-failure-as-absence violation: {v}" for v in failure_as_absence
    )
    reasons.extend(f"incomplete evidence: {v}" for v in incomplete_evidence)
    reasons.extend(f"nondeterministic scoring: {v}" for v in nondeterminism)
    reasons.extend(f"missing confidence field: {v}" for v in missing_confidence)

    passed = not reasons
    metrics: dict[str, object] = {
        "companies_total": len(scored),
        "homepage_fetch_success_rate": round(homepage_rate, 3),
        "relevant_page_inspected_rate": round(page_rate, 3),
        "companies_decision_grade": decision_grade_count,
        "companies_not_decision_grade": len(scored) - decision_grade_count,
        "failure_as_absence_violations": len(failure_as_absence),
        "incomplete_evidence_records": len(incomplete_evidence),
        "nondeterministic_scoring_records": len(nondeterminism),
        "legacy_false_defaults_removed": True,  # structural: EvidenceStatus has no boolean-false default
    }

    return GateResult(
        passed=passed,
        run_status="DECISION_GRADE" if passed else "NOT_DECISION_GRADE",
        metrics=metrics,
        failure_reasons=reasons,
    )
