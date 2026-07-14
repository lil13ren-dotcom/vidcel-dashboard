from lighthouse.analysis import scoring_v2
from lighthouse.models import (
    AcquisitionMetadata,
    Evidence,
    EvidenceSignals,
    RawCompanyV2,
    Social,
    WEBSITE_SIGNAL_KEYS,
)

NOW = "2026-01-01T00:00:00Z"
VERSION = "test-1.0"


def _all_unknown_signals() -> EvidenceSignals:
    return EvidenceSignals(
        {k: Evidence.unknown("not fetched", NOW, VERSION) for k in WEBSITE_SIGNAL_KEYS}
    )


def _all_present_signals() -> EvidenceSignals:
    return EvidenceSignals(
        {
            k: Evidence.present("https://x.example/", "found it", NOW, VERSION)
            for k in WEBSITE_SIGNAL_KEYS
        }
    )


def _company(
    signals, acquisition=None, rating=4.8, review_count=120, social=None
) -> RawCompanyV2:
    return RawCompanyV2(
        id="test-01",
        industry="Roofing",
        name="Test Co",
        website="https://x.example/",
        city="Austin",
        state="TX",
        website_signals=signals,
        social=social or Social(),
        acquisition=acquisition
        or AcquisitionMetadata(
            homepage_status="success",
            pages_attempted=3,
            pages_fetched=3,
            method_used="http",
            run_at=NOW,
            collector_version=VERSION,
        ),
        rating=rating,
        review_count=review_count,
    )


def test_coverage_ratio_zero_when_all_unknown() -> None:
    signals = _all_unknown_signals()
    assert scoring_v2.coverage_ratio(signals, scoring_v2.WEBSITE_CORE_SIGNALS) == 0.0
    assert scoring_v2.observed_score(signals, scoring_v2.WEBSITE_CORE_SIGNALS) is None


def test_coverage_ratio_one_when_all_present() -> None:
    signals = _all_present_signals()
    assert scoring_v2.coverage_ratio(signals, scoring_v2.WEBSITE_CORE_SIGNALS) == 1.0
    assert scoring_v2.observed_score(signals, scoring_v2.WEBSITE_CORE_SIGNALS) == 100.0


def test_partial_coverage_only_scores_confirmed_signals() -> None:
    keys = scoring_v2.WEBSITE_CORE_SIGNALS
    evidence = {k: Evidence.unknown("x", NOW, VERSION) for k in WEBSITE_SIGNAL_KEYS}
    # confirm exactly 2 of the core signals: one present, one absent
    evidence[keys[0]] = Evidence.present("u", "t", NOW, VERSION)
    evidence[keys[1]] = Evidence.absent("u", NOW, VERSION)
    signals = EvidenceSignals(evidence)

    coverage = scoring_v2.coverage_ratio(signals, keys)
    observed = scoring_v2.observed_score(signals, keys)
    assert coverage == 2 / len(keys)
    assert observed == 50.0  # 1 present out of 2 confirmed


def test_decision_grade_score_none_below_threshold() -> None:
    assert scoring_v2.decision_grade_score(90.0, 0.2, threshold=0.6) is None
    assert scoring_v2.decision_grade_score(90.0, 0.8, threshold=0.6) == 90.0
    assert scoring_v2.decision_grade_score(None, 0.9) is None


def test_google_score_none_when_rating_unconfirmed() -> None:
    company = _company(_all_present_signals(), rating=None, review_count=None)
    score, coverage = scoring_v2.google_score(company)
    assert score is None
    assert coverage == 0.0


def test_google_score_matches_v1_formula_when_confirmed() -> None:
    company = _company(_all_present_signals(), rating=5.0, review_count=200)
    score, coverage = scoring_v2.google_score(company)
    assert score == 100.0
    assert coverage == 1.0


def test_social_and_video_score_are_unscored_when_no_pages_fetched() -> None:
    acquisition = AcquisitionMetadata(
        homepage_status="policy_blocked",
        pages_attempted=1,
        pages_fetched=0,
        method_used="none",
        run_at=NOW,
        collector_version=VERSION,
    )
    company = _company(_all_unknown_signals(), acquisition=acquisition)
    score, coverage = scoring_v2.social_score(company)
    assert score is None
    assert coverage == 0.0


def test_overall_opportunity_score_none_when_no_gap_category_is_decision_grade() -> (
    None
):
    acquisition = AcquisitionMetadata(
        homepage_status="policy_blocked",
        pages_attempted=1,
        pages_fetched=0,
        method_used="none",
        run_at=NOW,
        collector_version=VERSION,
    )
    company = _company(_all_unknown_signals(), acquisition=acquisition)
    result = scoring_v2.score_company(company)
    assert result["overall_opportunity_score"] is None
    assert result["is_decision_grade"] is False


def test_overall_opportunity_score_computed_when_fully_confirmed() -> None:
    social = Social(
        instagram="https://instagram.com/x",
        facebook="https://facebook.com/x",
        youtube="https://youtube.com/x",
        tiktok="https://tiktok.com/x",
    )
    company = _company(
        _all_present_signals(), rating=5.0, review_count=200, social=social
    )
    result = scoring_v2.score_company(company)
    # fully present signals + full social presence -> maturity 100 -> gap 0 -> opportunity 0
    assert result["overall_opportunity_score"] == 0.0
    assert result["is_decision_grade"] is True


def test_overall_opportunity_score_rewards_demand_with_gap() -> None:
    evidence = {k: Evidence.absent("u", NOW, VERSION) for k in WEBSITE_SIGNAL_KEYS}
    signals = EvidenceSignals(evidence)
    company = _company(signals, rating=5.0, review_count=200)
    result = scoring_v2.score_company(company)
    assert result["overall_opportunity_score"] == 100.0  # max demand, max gap


def test_scoring_is_deterministic_across_repeated_calls() -> None:
    company = _company(_all_present_signals(), rating=4.6, review_count=80)
    first = scoring_v2.score_company(company)
    second = scoring_v2.score_company(company)
    assert first == second
