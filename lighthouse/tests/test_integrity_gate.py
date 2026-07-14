from lighthouse.analysis import integrity_gate, scoring_v2
from lighthouse.models import (
    AcquisitionMetadata,
    Evidence,
    EvidenceSignals,
    RawCompanyV2,
    ScoredCompanyV2,
    Social,
    WEBSITE_SIGNAL_KEYS,
)

NOW = "2026-01-01T00:00:00Z"
VERSION = "test-1.0"


def _company(
    company_id, pages_fetched, homepage_status="success", signals=None
) -> RawCompanyV2:
    signals = signals or EvidenceSignals(
        {
            k: Evidence.present("https://x.example/", "t", NOW, VERSION)
            for k in WEBSITE_SIGNAL_KEYS
        }
    )
    return RawCompanyV2(
        id=company_id,
        industry="Roofing",
        name=company_id,
        website="https://x.example/",
        city="Austin",
        state="TX",
        website_signals=signals,
        social=Social(),
        acquisition=AcquisitionMetadata(
            homepage_status=homepage_status,
            pages_attempted=3,
            pages_fetched=pages_fetched,
            method_used="http" if pages_fetched else "none",
            run_at=NOW,
            collector_version=VERSION,
        ),
        rating=4.8,
        review_count=150,
    )


def _scored(company) -> ScoredCompanyV2:
    result = scoring_v2.score_company(company)
    return ScoredCompanyV2(
        company=company,
        observed_score=result["observed_score"],
        coverage_ratio=result["coverage_ratio"],
        decision_grade=result["decision_grade"],
        overall_opportunity_score=result["overall_opportunity_score"],
        data_coverage_ratio=result["data_coverage_ratio"],
        data_confidence=result["data_confidence"],
        is_decision_grade=result["is_decision_grade"],
        decision_grade_reason=result["decision_grade_reason"],
        opportunities=[],
        journey={},
        top_customer_words=[],
        high_opportunity_gaps=[],
    )


def test_gate_passes_when_all_companies_fetch_successfully() -> None:
    companies = [_company(f"c{i}", pages_fetched=3) for i in range(10)]
    scored = [_scored(c) for c in companies]
    result = integrity_gate.evaluate(scored, companies)
    assert result.passed is True
    assert result.run_status == "DECISION_GRADE"


def test_gate_fails_when_homepage_success_rate_below_threshold() -> None:
    companies = [_company(f"c{i}", pages_fetched=3) for i in range(2)]
    companies += [
        _company(f"c{i}", pages_fetched=0, homepage_status="policy_blocked")
        for i in range(8)
    ]
    scored = [_scored(c) for c in companies]
    result = integrity_gate.evaluate(scored, companies)
    assert result.passed is False
    assert result.run_status == "NOT_DECISION_GRADE"
    assert any(
        "homepage direct-fetch success rate" in r for r in result.failure_reasons
    )
    assert result.metrics["homepage_fetch_success_rate"] == 0.2


def test_gate_detects_failure_represented_as_absence() -> None:
    """Construct a deliberately-broken record (simulating a bug elsewhere
    in the pipeline) to prove the gate actually catches this, rather than
    just trusting the extractor never produces it.
    """
    broken_signals = EvidenceSignals(
        {
            k: Evidence.absent("https://x.example/", NOW, VERSION)
            for k in WEBSITE_SIGNAL_KEYS
        }
    )
    company = _company(
        "broken",
        pages_fetched=0,
        homepage_status="policy_blocked",
        signals=broken_signals,
    )
    scored = [_scored(company)]
    result = integrity_gate.evaluate(scored, [company])
    assert result.passed is False
    assert any(
        "acquisition-failure-as-absence violation" in r for r in result.failure_reasons
    )


def test_gate_ignores_https_exemption_for_failure_as_absence_check() -> None:
    """https is legitimately allowed to be confirmed independent of
    pages_fetched (see signal_extractor._RESPONSE_RECEIVED_STATUSES), so
    the gate must not flag it as a violation on its own.
    """
    signals = EvidenceSignals(
        {
            k: (
                Evidence.absent("u", NOW, VERSION)
                if k == "https"
                else Evidence.unknown("x", NOW, VERSION)
            )
            for k in WEBSITE_SIGNAL_KEYS
        }
    )
    company = _company(
        "c1", pages_fetched=0, homepage_status="http_error", signals=signals
    )
    scored = [_scored(company)]
    result = integrity_gate.evaluate(scored, [company])
    assert not any("'https'" in r for r in result.failure_reasons)


def test_gate_detects_nondeterministic_scoring(monkeypatch) -> None:
    company = _company("c1", pages_fetched=3)
    scored = [_scored(company)]

    call_count = {"n": 0}
    real_score_company = scoring_v2.score_company

    def flaky_score_company(c) -> dict:
        call_count["n"] += 1
        result = real_score_company(c)
        if call_count["n"] % 2 == 0:
            result = dict(result)
            result["overall_opportunity_score"] = (
                result["overall_opportunity_score"] or 0
            ) + 1
        return result

    monkeypatch.setattr(scoring_v2, "score_company", flaky_score_company)
    result = integrity_gate.evaluate(scored, [company])
    assert any("nondeterministic scoring" in r for r in result.failure_reasons)


def test_gate_metrics_report_decision_grade_split() -> None:
    unknown_signals = EvidenceSignals(
        {k: Evidence.unknown("x", NOW, VERSION) for k in WEBSITE_SIGNAL_KEYS}
    )
    companies = [_company(f"c{i}", pages_fetched=3) for i in range(9)]
    companies.append(
        _company(
            "blocked",
            pages_fetched=0,
            homepage_status="policy_blocked",
            signals=unknown_signals,
        )
    )
    scored = [_scored(c) for c in companies]
    result = integrity_gate.evaluate(scored, companies)
    assert result.metrics["companies_total"] == 10
    assert result.metrics["companies_decision_grade"] == 9
    assert result.metrics["companies_not_decision_grade"] == 1
